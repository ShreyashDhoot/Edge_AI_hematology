#!/usr/bin/env python3
"""
paper_eval.py  --  One-shot evaluation suite for the Edge-AI haematology paper.

Run from the ROOT of your Edge_AI_hematology repo (same folder as train.py):

    python paper_eval.py \
        --weights runs/detect/outputs/checkpoints/yolov8n_hematology/weights/best.pt \
        --bccd_test  data/BCCD_r/BCCD/yolo_format \
        --clinical_dir data/clinical_72 \
        --out paper_results

It produces, in --out/ :
    results.json                      every number used in the paper
    table_*.tex                       LaTeX table bodies you can \\input{}
    fig_*.pdf                         all figures for the paper
    paper_numbers.tex                 \\newcommand macros (so the paper auto-fills)

WHAT IT COMPUTES (maps to the advisor's "compare to existing methods" ask)
  A. Detection metrics on BCCD test split and on the 72-image OOD set
        precision / recall / F1 / AP@0.5 / mAP@0.5:0.95 + Wilson CIs
  B. Method-comparison statistics (CLSI EP09c style) vs. human reference
        Pearson r (+ bootstrap CI), Spearman, ICC(2,1) (+ CI),
        Bland-Altman bias & 95% LoA (+ bootstrap CI),
        TRUE Passing-Bablok (slope/intercept with CIs) and Deming regression,
        MAPE, MAE
  C. Repeatability CV%  (Protocol A field-to-field, Protocol B perturbation)
  D. Human-vs-human inter-annotator baseline (needs --second_annotator_dir)
  E. Calibration: ECE + reliability diagram
  F. Robustness curves (blur / stain shift / brightness / obscuration)
  G. Quantisation trade-off: FP32 vs FP16 vs INT8 (size, latency, accuracy)
  H. Model comparison: YOLOv8n vs SSDLite (optional)
  I. Domain-shift fix: stain normalisation + threshold tuning on split of the 72

Every section is wrapped so that a missing input SKIPS that section rather than
crashing the run.  Read the console summary at the end.

Dependencies: numpy scipy pandas matplotlib opencv-python ultralytics onnxruntime
"""
import os, sys, json, time, glob, argparse, warnings, math
import numpy as np
import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

warnings.filterwarnings("ignore")
CLASS_NAMES = ["RBC", "WBC", "Platelets"]
RNG = np.random.default_rng(42)

plt.rcParams.update({
    "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8,
    "legend.fontsize": 7, "xtick.labelsize": 7, "ytick.labelsize": 7,
    "figure.dpi": 150, "savefig.bbox": "tight", "font.family": "serif",
})

# ----------------------------------------------------------------------------
# generic statistics
# ----------------------------------------------------------------------------
def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def boot_ci(fn, *arrs, n_boot=2000, alpha=0.05):
    arrs = [np.asarray(a, float) for a in arrs]
    n = len(arrs[0])
    vals = []
    for _ in range(n_boot):
        idx = RNG.integers(0, n, n)
        try:
            v = fn(*[a[idx] for a in arrs])
            if np.isfinite(v):
                vals.append(v)
        except Exception:
            pass
    if not vals:
        return (float("nan"), float("nan"))
    return (float(np.percentile(vals, 100 * alpha / 2)),
            float(np.percentile(vals, 100 * (1 - alpha / 2))))


def safe_pearson(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.std() < 1e-9 or b.std() < 1e-9:
        return float("nan")
    return float(stats.pearsonr(a, b)[0])


def icc_2_1(x, y):
    """ICC(2,1): two-way random effects, absolute agreement, single measure."""
    data = np.column_stack([np.asarray(x, float), np.asarray(y, float)])
    n, k = data.shape
    gm = data.mean()
    ssr = k * np.sum((data.mean(1) - gm) ** 2)
    ssc = n * np.sum((data.mean(0) - gm) ** 2)
    sst = np.sum((data - gm) ** 2)
    sse = sst - ssr - ssc
    msr, msc = ssr / (n - 1), ssc / (k - 1)
    mse = sse / ((n - 1) * (k - 1))
    denom = msr + (k - 1) * mse + k * (msc - mse) / n
    return float((msr - mse) / denom) if denom != 0 else float("nan")


def bland_altman(sys_c, ref_c):
    s, r = np.asarray(sys_c, float), np.asarray(ref_c, float)
    d = s - r
    bias, sd = d.mean(), d.std(ddof=1)
    out = dict(bias=float(bias), sd=float(sd),
               loa_lo=float(bias - 1.96 * sd), loa_hi=float(bias + 1.96 * sd), n=int(len(d)))
    out["bias_ci"] = boot_ci(lambda a, b: (a - b).mean(), s, r)
    out["loa_lo_ci"] = boot_ci(lambda a, b: (a - b).mean() - 1.96 * (a - b).std(ddof=1), s, r)
    out["loa_hi_ci"] = boot_ci(lambda a, b: (a - b).mean() + 1.96 * (a - b).std(ddof=1), s, r)
    # proportional bias test: regress d on mean
    m = (s + r) / 2
    if m.std() > 1e-9:
        sl, ic, rv, pv, _ = stats.linregress(m, d)
        out["prop_bias_slope"], out["prop_bias_p"] = float(sl), float(pv)
    return out


def passing_bablok(x, y, alpha=0.05):
    """
    Proper Passing-Bablok (1983): shifted median of pairwise slopes, with the
    slope==-1 exclusion and K offset correction, and analytic confidence
    intervals.  x = reference method, y = new method.
    Returns slope, intercept and 95% CIs.
    """
    x, y = np.asarray(x, float), np.asarray(y, float)
    n = len(x)
    S = []
    for i in range(n - 1):
        for j in range(i + 1, n):
            dx, dy = x[j] - x[i], y[j] - y[i]
            if dx == 0 and dy == 0:
                continue
            if dx == 0:
                s = np.inf if dy > 0 else -np.inf
            else:
                s = dy / dx
            if s == -1:
                continue
            S.append(s)
    S = np.sort(np.array(S))
    N = len(S)
    if N == 0:
        return dict(slope=float("nan"), intercept=float("nan"))
    K = int(np.sum(S < -1))
    if N % 2:
        b = S[(N + 1) // 2 + K - 1]
    else:
        b = 0.5 * (S[N // 2 + K - 1] + S[N // 2 + K])
    a = float(np.median(y - b * x))
    C = stats.norm.ppf(1 - alpha / 2) * math.sqrt(n * (n - 1) * (2 * n + 5) / 18.0)
    M1 = int(round((N - C) / 2))
    M2 = N - M1 + 1
    lo_i, hi_i = M1 + K - 1, M2 + K - 1
    lo_i = int(np.clip(lo_i, 0, N - 1)); hi_i = int(np.clip(hi_i, 0, N - 1))
    b_lo, b_hi = S[lo_i], S[hi_i]
    a_lo = float(np.median(y - b_hi * x)); a_hi = float(np.median(y - b_lo * x))
    return dict(slope=float(b), slope_ci=(float(b_lo), float(b_hi)),
                intercept=a, intercept_ci=(min(a_lo, a_hi), max(a_lo, a_hi)))


def deming(x, y, delta=1.0):
    x, y = np.asarray(x, float), np.asarray(y, float)
    mx, my = x.mean(), y.mean()
    sxx = np.sum((x - mx) ** 2) / (len(x) - 1)
    syy = np.sum((y - my) ** 2) / (len(x) - 1)
    sxy = np.sum((x - mx) * (y - my)) / (len(x) - 1)
    if sxy == 0:
        return dict(slope=float("nan"), intercept=float("nan"))
    b = (syy - delta * sxx + math.sqrt((syy - delta * sxx) ** 2 + 4 * delta * sxy ** 2)) / (2 * sxy)
    return dict(slope=float(b), intercept=float(my - b * mx))


def agreement_bundle(sys_c, ref_c):
    s, r = np.asarray(sys_c, float), np.asarray(ref_c, float)
    out = dict(n=int(len(s)))
    out["pearson_r"] = safe_pearson(s, r)
    out["pearson_ci"] = boot_ci(safe_pearson, s, r)
    if s.std() > 1e-9 and r.std() > 1e-9:
        out["spearman_rho"] = float(stats.spearmanr(s, r)[0])
    else:
        out["spearman_rho"] = float("nan")
    out["icc21"] = icc_2_1(s, r)
    out["icc21_ci"] = boot_ci(icc_2_1, s, r)
    out["mae"] = float(np.mean(np.abs(s - r)))
    nz = r != 0
    out["mape"] = float(np.mean(np.abs((s[nz] - r[nz]) / r[nz])) * 100) if nz.any() else float("nan")
    out["mean_ref"] = float(r.mean())
    out["ba"] = bland_altman(s, r)
    out["pb"] = passing_bablok(r, s)
    out["deming"] = deming(r, s)
    return out


def cv_percent(counts):
    c = np.asarray(counts, float)
    if len(c) < 2 or c.mean() == 0:
        return float("nan")
    return float(c.std(ddof=1) / c.mean() * 100)


# ----------------------------------------------------------------------------
# data loading (YOLO txt or VOC xml, auto-detected)
# ----------------------------------------------------------------------------
def load_gt_yolo(label_path, w, h):
    boxes, labels = [], []
    if os.path.exists(label_path):
        for ln in open(label_path):
            p = ln.split()
            if len(p) < 5:
                continue
            c, xc, yc, bw, bh = int(p[0]), *map(float, p[1:5])
            boxes.append([(xc - bw / 2) * w, (yc - bh / 2) * h, (xc + bw / 2) * w, (yc + bh / 2) * h])
            labels.append(c + 1)
    return np.array(boxes, np.float32).reshape(-1, 4), np.array(labels, np.int64)


def load_gt_voc(xml_path):
    import xml.etree.ElementTree as ET
    boxes, labels = [], []
    if not os.path.exists(xml_path):
        return np.zeros((0, 4), np.float32), np.zeros((0,), np.int64)
    for obj in ET.parse(xml_path).getroot().findall("object"):
        nm = obj.find("name").text.strip().lower()
        idx = None
        for i, k in enumerate(CLASS_NAMES, 1):
            if k.lower() in nm or (k == "Platelets" and "platelet" in nm):
                idx = i; break
        if idx is None:
            continue
        b = obj.find("bndbox")
        x1, y1, x2, y2 = [float(b.find(t).text) for t in ("xmin", "ymin", "xmax", "ymax")]
        if x2 > x1 and y2 > y1:
            boxes.append([x1, y1, x2, y2]); labels.append(idx)
    return np.array(boxes, np.float32).reshape(-1, 4), np.array(labels, np.int64)


def find_dataset(root):
    """Returns list of (img_path, boxes, labels). Handles several layouts."""
    items = []
    imgs = []
    for ext in ("jpg", "jpeg", "png", "JPG", "PNG"):
        imgs += glob.glob(os.path.join(root, "**", f"*.{ext}"), recursive=True)
    imgs = sorted(set(imgs))
    for ip in imgs:
        base = os.path.splitext(ip)[0]
        d = os.path.dirname(ip)
        img = cv2.imread(ip)
        if img is None:
            continue
        h, w = img.shape[:2]
        cands_txt = [base + ".txt",
                     ip.replace(f"{os.sep}images{os.sep}", f"{os.sep}labels{os.sep}").rsplit(".", 1)[0] + ".txt"]
        cands_xml = [base + ".xml",
                     os.path.join(os.path.dirname(d), "Annotations", os.path.basename(base) + ".xml"),
                     os.path.join(d, "Annotations", os.path.basename(base) + ".xml")]
        got = None
        for t in cands_txt:
            if os.path.exists(t):
                got = load_gt_yolo(t, w, h); break
        if got is None:
            for x in cands_xml:
                if os.path.exists(x):
                    got = load_gt_voc(x); break
        if got is not None:
            items.append((ip, got[0], got[1]))
    return items


# ----------------------------------------------------------------------------
# model wrappers  (all return dict(boxes, scores, labels[1..3]))
# ----------------------------------------------------------------------------
class YoloPT:
    def __init__(self, path, conf=0.25, imgsz=640):
        from ultralytics import YOLO
        self.m = YOLO(path); self.conf = conf; self.imgsz = imgsz

    def __call__(self, bgr, conf=None):
        r = self.m.predict(bgr, conf=conf if conf is not None else self.conf,
                           imgsz=self.imgsz, verbose=False, iou=0.5)[0]
        b = r.boxes
        return dict(boxes=b.xyxy.cpu().numpy() if len(b) else np.zeros((0, 4)),
                    scores=b.conf.cpu().numpy() if len(b) else np.zeros(0),
                    labels=(b.cls.cpu().numpy().astype(int) + 1) if len(b) else np.zeros(0, int))


class YoloONNX:
    """Runs an Ultralytics-exported YOLOv8 ONNX (FP32/FP16/INT8) with numpy NMS."""
    def __init__(self, path, conf=0.25, imgsz=640, threads=4):
        import onnxruntime as ort
        so = ort.SessionOptions(); so.intra_op_num_threads = threads
        self.s = ort.InferenceSession(path, so, providers=["CPUExecutionProvider"])
        self.inp = self.s.get_inputs()[0]
        self.conf, self.imgsz = conf, imgsz
        self.dtype = np.float16 if "float16" in self.inp.type else np.float32

    def __call__(self, bgr, conf=None):
        conf = self.conf if conf is None else conf
        h0, w0 = bgr.shape[:2]
        img = cv2.resize(bgr, (self.imgsz, self.imgsz))
        x = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).transpose(2, 0, 1)[None].astype(np.float32) / 255.0
        out = self.s.run(None, {self.inp.name: x.astype(self.dtype)})[0][0].astype(np.float32)  # (4+nc, N)
        if out.shape[0] < out.shape[1]:
            out = out.T
        boxes = out[:, :4]; cls_sc = out[:, 4:]
        sc = cls_sc.max(1); cl = cls_sc.argmax(1)
        keep = sc >= conf
        boxes, sc, cl = boxes[keep], sc[keep], cl[keep]
        xyxy = np.stack([boxes[:, 0] - boxes[:, 2] / 2, boxes[:, 1] - boxes[:, 3] / 2,
                         boxes[:, 0] + boxes[:, 2] / 2, boxes[:, 1] + boxes[:, 3] / 2], 1)
        xyxy[:, [0, 2]] *= w0 / self.imgsz; xyxy[:, [1, 3]] *= h0 / self.imgsz
        idx = cv2.dnn.NMSBoxes([[float(a), float(b), float(c - a), float(d - b)] for a, b, c, d in xyxy],
                               sc.tolist(), conf, 0.5) if len(sc) else []
        idx = np.array(idx).flatten().astype(int) if len(idx) else np.array([], int)
        return dict(boxes=xyxy[idx], scores=sc[idx], labels=cl[idx] + 1)


class SSDLitePT:
    def __init__(self, path, conf=0.25):
        import torch
        sys.path.insert(0, os.getcwd())
        from models.ssdlite_mobilenetv3 import build_ssdlite_mobilenetv3
        self.torch = torch
        self.m = build_ssdlite_mobilenetv3(num_classes=4, pretrained=False)
        self.m.load_state_dict(torch.load(path, map_location="cpu")); self.m.eval()
        self.conf = conf

    def __call__(self, bgr, conf=None):
        conf = self.conf if conf is None else conf
        h0, w0 = bgr.shape[:2]
        img = cv2.resize(bgr, (320, 320))
        t = self.torch.from_numpy(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).permute(2, 0, 1).float() / 255
        with self.torch.no_grad():
            o = self.m([t])[0]
        b = o["boxes"].numpy().copy(); s = o["scores"].numpy(); l = o["labels"].numpy()
        b[:, [0, 2]] *= w0 / 320; b[:, [1, 3]] *= h0 / 320
        k = s >= conf
        return dict(boxes=b[k], scores=s[k], labels=l[k])


# ----------------------------------------------------------------------------
# detection metrics
# ----------------------------------------------------------------------------
def iou_mat(a, b):
    if len(a) == 0 or len(b) == 0:
        return np.zeros((len(a), len(b)))
    x1 = np.maximum(a[:, None, 0], b[None, :, 0]); y1 = np.maximum(a[:, None, 1], b[None, :, 1])
    x2 = np.minimum(a[:, None, 2], b[None, :, 2]); y2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    aa = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1]); bb = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    return inter / (aa[:, None] + bb[None] - inter + 1e-9)


def match_class(preds, gts, cls, thr):
    """Return (scores, tp flags, n_gt) for one class at one IoU thr, greedy by score."""
    S, T, npos = [], [], 0
    for p, g in zip(preds, gts):
        gb = g["boxes"][g["labels"] == cls]; npos += len(gb)
        pm = p["labels"] == cls; pb, ps = p["boxes"][pm], p["scores"][pm]
        order = np.argsort(-ps); pb, ps = pb[order], ps[order]
        used = np.zeros(len(gb), bool)
        M = iou_mat(pb, gb)
        for i in range(len(pb)):
            S.append(ps[i]); hit = 0
            if len(gb):
                j = int(np.argmax(np.where(used, -1, M[i])))
                if not used[j] and M[i, j] >= thr:
                    used[j] = True; hit = 1
            T.append(hit)
    return np.array(S), np.array(T), npos


def ap_from(S, T, npos):
    if npos == 0:
        return float("nan")
    if len(S) == 0:
        return 0.0
    o = np.argsort(-S); tp = np.cumsum(T[o]); fp = np.cumsum(1 - T[o])
    rec = tp / npos; prec = tp / np.maximum(tp + fp, 1e-9)
    mrec = np.concatenate([[0], rec, [1]]); mpre = np.concatenate([[1], prec, [0]])
    for i in range(len(mpre) - 2, -1, -1):
        mpre[i] = max(mpre[i], mpre[i + 1])
    idx = np.where(mrec[1:] != mrec[:-1])[0]
    return float(np.sum((mrec[idx + 1] - mrec[idx]) * mpre[idx + 1]))


def detection_metrics(preds, gts):
    out = {}
    for ci, cn in enumerate(CLASS_NAMES, 1):
        S, T, n = match_class(preds, gts, ci, 0.5)
        tp = int(T.sum()); fp = int(len(T) - tp); fn = int(n - tp)
        P = tp / max(tp + fp, 1); R = tp / max(n, 1); F1 = 2 * P * R / max(P + R, 1e-9)
        aps = [ap_from(*match_class(preds, gts, ci, t)) for t in np.arange(0.5, 0.96, 0.05)]
        out[cn] = dict(tp=tp, fp=fp, fn=fn, n_gt=int(n), precision=P, recall=R, f1=F1,
                       ap50=ap_from(S, T, n), ap5095=float(np.nanmean(aps)),
                       p_ci=wilson(tp, tp + fp), r_ci=wilson(tp, n))
    out["mAP50"] = float(np.nanmean([out[c]["ap50"] for c in CLASS_NAMES]))
    out["mAP5095"] = float(np.nanmean([out[c]["ap5095"] for c in CLASS_NAMES]))
    return out


def counts_from(preds, gts):
    P = {c: [int(np.sum(p["labels"] == i)) for p in preds] for i, c in enumerate(CLASS_NAMES, 1)}
    G = {c: [int(np.sum(g["labels"] == i)) for g in gts] for i, c in enumerate(CLASS_NAMES, 1)}
    return P, G


def run_model(model, items, conf=None, preprocess=None):
    preds, gts = [], []
    for ip, b, l in items:
        img = cv2.imread(ip)
        if preprocess is not None:
            img = preprocess(img)
        preds.append(model(img, conf) if conf is not None else model(img))
        gts.append(dict(boxes=b, labels=l))
    return preds, gts


def confusion(preds, gts, thr=0.5):
    """3 classes + background. rows=pred, cols=true."""
    K = len(CLASS_NAMES); M = np.zeros((K + 1, K + 1), int)
    for p, g in zip(preds, gts):
        Mi = iou_mat(p["boxes"], g["boxes"]); used_g = set(); used_p = set()
        if Mi.size:
            pairs = sorted([(Mi[i, j], i, j) for i in range(Mi.shape[0]) for j in range(Mi.shape[1])
                            if Mi[i, j] >= thr], reverse=True)
            for _, i, j in pairs:
                if i in used_p or j in used_g:
                    continue
                used_p.add(i); used_g.add(j)
                M[p["labels"][i] - 1, g["labels"][j] - 1] += 1
        for i in range(len(p["boxes"])):
            if i not in used_p:
                M[p["labels"][i] - 1, K] += 1
        for j in range(len(g["boxes"])):
            if j not in used_g:
                M[K, g["labels"][j] - 1] += 1
    return M


# ----------------------------------------------------------------------------
# plotting
# ----------------------------------------------------------------------------
def fig_bland_altman(all_ba, title, path):
    fig, ax = plt.subplots(1, 3, figsize=(7.2, 2.3))
    for a, c in zip(ax, CLASS_NAMES):
        s, r = np.asarray(all_ba[c][0], float), np.asarray(all_ba[c][1], float)
        m, d = (s + r) / 2, s - r
        bias, sd = d.mean(), d.std(ddof=1)
        a.scatter(m, d, s=8, alpha=.6, edgecolors="k", linewidths=.3)
        a.axhline(bias, color="r", ls="--", lw=1)
        a.axhline(bias + 1.96 * sd, color="gray", ls=":", lw=1)
        a.axhline(bias - 1.96 * sd, color="gray", ls=":", lw=1)
        a.axhline(0, color="k", lw=.4)
        a.set_title(f"{c}: bias={bias:.1f}, LoA [{bias-1.96*sd:.1f}, {bias+1.96*sd:.1f}]")
        a.set_xlabel("mean of methods"); a.set_ylabel("system $-$ human")
        a.grid(alpha=.3)
    fig.suptitle(title, y=1.04, fontsize=8)
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


def fig_scatter_pb(all_ba, title, path):
    fig, ax = plt.subplots(1, 3, figsize=(7.2, 2.3))
    for a, c in zip(ax, CLASS_NAMES):
        s, r = np.asarray(all_ba[c][0], float), np.asarray(all_ba[c][1], float)
        a.scatter(r, s, s=8, alpha=.6, edgecolors="k", linewidths=.3)
        lim = [0, max(r.max(), s.max()) * 1.05 + 1]
        a.plot(lim, lim, "k--", lw=.8, label="identity")
        pb = passing_bablok(r, s)
        if np.isfinite(pb.get("slope", np.nan)):
            xs = np.array(lim)
            a.plot(xs, pb["intercept"] + pb["slope"] * xs, "r-", lw=1,
                   label=f"P-B: y={pb['slope']:.2f}x+{pb['intercept']:.1f}")
        a.set_xlim(lim); a.set_ylim(lim)
        a.set_title(c); a.set_xlabel("human count"); a.set_ylabel("system count")
        a.legend(loc="upper left"); a.grid(alpha=.3)
    fig.suptitle(title, y=1.04, fontsize=8)
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


def fig_confusion(M, path, title):
    names = CLASS_NAMES + ["BG"]
    Mn = M / np.maximum(M.sum(0, keepdims=True), 1)
    fig, ax = plt.subplots(figsize=(3.2, 2.8))
    im = ax.imshow(Mn, cmap="Blues", vmin=0, vmax=1)
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            ax.text(j, i, f"{Mn[i,j]:.2f}\n({M[i,j]})", ha="center", va="center", fontsize=6,
                    color="white" if Mn[i, j] > .5 else "black")
    ax.set_xticks(range(4)); ax.set_xticklabels(names); ax.set_yticks(range(4)); ax.set_yticklabels(names)
    ax.set_xlabel("ground truth"); ax.set_ylabel("predicted"); ax.set_title(title)
    fig.colorbar(im, fraction=.046); fig.tight_layout(); fig.savefig(path); plt.close(fig)


# ----------------------------------------------------------------------------
# corruption functions for robustness
# ----------------------------------------------------------------------------
def c_blur(img, s):
    k = int([1, 3, 5, 9, 15][s]) | 1
    return img if s == 0 else cv2.GaussianBlur(img, (k, k), 0)


def c_stain(img, s):
    """Simulated stain colour shift in HSV (hue rotation + saturation drop)."""
    if s == 0:
        return img
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 0] = (hsv[..., 0] + [0, 4, 8, 14, 20][s]) % 180
    hsv[..., 1] *= [1, .9, .75, .6, .45][s]
    return cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2BGR)


def c_bright(img, s):
    f = [1, 0.85, 0.7, 0.55, 0.4][s]
    return np.clip(img.astype(np.float32) * f, 0, 255).astype(np.uint8)


def c_noise(img, s):
    sg = [0, 5, 12, 20, 32][s]
    return img if s == 0 else np.clip(img + RNG.normal(0, sg, img.shape), 0, 255).astype(np.uint8)


def c_obscure(img, s):
    """Occlusion by random dark patches (dust / debris / bubbles)."""
    if s == 0:
        return img
    o = img.copy(); h, w = o.shape[:2]
    for _ in range([0, 2, 4, 7, 10][s]):
        pw, ph = int(w * RNG.uniform(.04, .1)), int(h * RNG.uniform(.04, .1))
        x, y = RNG.integers(0, w - pw), RNG.integers(0, h - ph)
        o[y:y + ph, x:x + pw] = (o[y:y + ph, x:x + pw] * 0.2).astype(np.uint8)
    return o


CORRUPTIONS = {"Gaussian blur": c_blur, "Stain shift": c_stain, "Illumination drop": c_bright,
               "Sensor noise": c_noise, "Obscuration": c_obscure}


def perturb_small(img):
    """Protocol B: realistic re-capture jitter."""
    h, w = img.shape[:2]
    ang = RNG.uniform(-3, 3)
    M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, 1.0)
    M[:, 2] += RNG.integers(-3, 4, 2)
    o = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REFLECT)
    return np.clip(o.astype(np.float32) * RNG.uniform(.92, 1.08) + RNG.uniform(-8, 8), 0, 255).astype(np.uint8)


# ----------------------------------------------------------------------------
# calibration
# ----------------------------------------------------------------------------
def calibration(preds, gts, thr=0.5, nb=10):
    conf, corr = [], []
    for ci in (1, 2, 3):
        S, T, _ = match_class(preds, gts, ci, thr)
        conf += list(S); corr += list(T)
    conf, corr = np.array(conf), np.array(corr)
    if len(conf) == 0:
        return None
    bins = np.linspace(0, 1, nb + 1); ece = 0; rows = []
    for i in range(nb):
        m = (conf > bins[i]) & (conf <= bins[i + 1])
        if m.sum():
            acc, cf = corr[m].mean(), conf[m].mean()
            ece += m.sum() / len(conf) * abs(acc - cf)
            rows.append((cf, acc, int(m.sum())))
    return dict(ece=float(ece), bins=rows, n=int(len(conf)))


def fig_reliability(cal_dict, path):
    fig, ax = plt.subplots(figsize=(3.2, 3.0))
    ax.plot([0, 1], [0, 1], "k--", lw=.8, label="perfect")
    for lab, cal in cal_dict.items():
        if cal:
            b = np.array(cal["bins"])
            ax.plot(b[:, 0], b[:, 1], "o-", ms=3, lw=1, label=f"{lab} (ECE={cal['ece']:.3f})")
    ax.set_xlabel("mean confidence"); ax.set_ylabel("precision (fraction correct)")
    ax.legend(); ax.grid(alpha=.3); fig.tight_layout(); fig.savefig(path); plt.close(fig)


# ----------------------------------------------------------------------------
# LaTeX helpers
# ----------------------------------------------------------------------------
def f(x, d=2):
    return "--" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{d}f}"


def ci(c, d=2):
    return f"[{f(c[0], d)}, {f(c[1], d)}]"


def write(path, txt):
    with open(path, "w") as fh:
        fh.write(txt)


# ============================================================================
# MAIN
# ============================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default="runs/detect/outputs/checkpoints/yolov8n_hematology/weights/best.pt")
    ap.add_argument("--onnx_fp32", default="runs/detect/outputs/checkpoints/yolov8n_hematology/weights/best.onnx")
    ap.add_argument("--onnx_int8", default="outputs/yolov8n_int8.onnx")
    ap.add_argument("--onnx_fp16", default="", help="optional FP16 ONNX")
    ap.add_argument("--ssd_weights", default="outputs/checkpoints/ssdlite_mobilenetv3_best.pth")
    ap.add_argument("--bccd_test", default="data/BCCD_r/BCCD/yolo_format/images/val",
                    help="BCCD held-out images (dir containing images + labels/annotations)")
    ap.add_argument("--clinical_dir", default="data/clinical_72")
    ap.add_argument("--second_annotator_dir", default="",
                    help="folder with the 2nd annotator labels for a subset of the 72 (same layout)")
    ap.add_argument("--fields_dir", default="", help="Protocol A: folder of 10-20 fields from ONE slide")
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--out", default="paper_results")
    ap.add_argument("--skip", nargs="*", default=[], help="sections to skip: robust quant repeat calib ssd tune")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    R = {}   # results registry
    macros = []

    def macro(name, val):
        macros.append(f"\\newcommand{{\\{name}}}{{{val}}}")

    def section(name):
        print(f"\n===== {name} =====")

    # -------- load model(s) -------------------------------------------------
    section("Loading")
    yolo = YoloPT(a.weights, a.conf) if os.path.exists(a.weights) else None
    print("YOLO .pt:", "ok" if yolo else "MISSING")
    if yolo is None:
        sys.exit("Need --weights to proceed.")

    bccd = find_dataset(a.bccd_test) if os.path.exists(a.bccd_test) else []
    clin = find_dataset(a.clinical_dir) if os.path.exists(a.clinical_dir) else []
    print(f"BCCD test images: {len(bccd)} | clinical images: {len(clin)}")
    R["n_bccd"], R["n_clin"] = len(bccd), len(clin)
    macro("nBCCD", len(bccd)); macro("nClin", len(clin))

    # -------- A + B  main results -------------------------------------------
    section("A/B. Detection + method-comparison (YOLOv8n FP32)")
    sets = {"BCCD": bccd, "Clinical72": clin}
    predcache = {}
    for name, items in sets.items():
        if not items:
            continue
        preds, gts = run_model(yolo, items)
        predcache[name] = (preds, gts)
        det = detection_metrics(preds, gts)
        P, G = counts_from(preds, gts)
        agr = {c: agreement_bundle(P[c], G[c]) for c in CLASS_NAMES}
        R[f"det_{name}"] = det; R[f"agree_{name}"] = agr
        M = confusion(preds, gts)
        R[f"conf_{name}"] = M.tolist()
        fig_confusion(M, os.path.join(a.out, f"fig_confusion_{name}.pdf"), f"YOLOv8n on {name}")
        fig_bland_altman({c: (P[c], G[c]) for c in CLASS_NAMES},
                         f"Bland--Altman: system vs. human counts ({name})",
                         os.path.join(a.out, f"fig_ba_{name}.pdf"))
        fig_scatter_pb({c: (P[c], G[c]) for c in CLASS_NAMES},
                       f"Passing--Bablok regression ({name})",
                       os.path.join(a.out, f"fig_pb_{name}.pdf"))
        print(f"{name}: mAP50={det['mAP50']:.3f}  mAP50-95={det['mAP5095']:.3f}")
        for c in CLASS_NAMES:
            print(f"   {c:9s} P={det[c]['precision']:.3f} R={det[c]['recall']:.3f} "
                  f"F1={det[c]['f1']:.3f}  r={agr[c]['pearson_r']:.3f} ICC={agr[c]['icc21']:.3f} "
                  f"bias={agr[c]['ba']['bias']:.2f}")
        macro(f"mAP{name}", f"{det['mAP50']:.3f}")
        macro(f"mAPfull{name}", f"{det['mAP5095']:.3f}")

    # detection table (BCCD vs clinical)
    if predcache:
        rows = []
        for c in CLASS_NAMES:
            r = []
            for name in ("BCCD", "Clinical72"):
                if f"det_{name}" in R:
                    d = R[f"det_{name}"][c]
                    r += [f(d["precision"]), f(d["recall"]), f(d["f1"]), f(d["ap50"])]
                else:
                    r += ["--"] * 4
            rows.append(f"{c} & " + " & ".join(r) + r" \\")
        write(os.path.join(a.out, "table_detection.tex"), "\n".join(rows))

        # agreement table
        rows = []
        for c in CLASS_NAMES:
            if "agree_Clinical72" in R:
                g = R["agree_Clinical72"][c]
                rows.append(
                    f"{c} & {f(g['pearson_r'])} {ci(g['pearson_ci'])} & {f(g['icc21'])} {ci(g['icc21_ci'])} & "
                    f"{f(g['ba']['bias'])} & [{f(g['ba']['loa_lo'],1)}, {f(g['ba']['loa_hi'],1)}] & "
                    f"{f(g['pb']['slope'])} & {f(g['pb']['intercept'],1)} & {f(g['mape'],1)} " + r"\\")
        write(os.path.join(a.out, "table_agreement.tex"), "\n".join(rows))

    # -------- D. Human vs human ---------------------------------------------
    if a.second_annotator_dir and os.path.exists(a.second_annotator_dir) and clin:
        section("D. Inter-annotator (human vs human)")
        second = {os.path.basename(p): (b, l) for p, b, l in find_dataset(a.second_annotator_dir)}
        H1, H2, Yc = {c: [] for c in CLASS_NAMES}, {c: [] for c in CLASS_NAMES}, {c: [] for c in CLASS_NAMES}
        for (ip, b1, l1), pr in zip(clin, predcache["Clinical72"][0]):
            k = os.path.basename(ip)
            if k in second:
                for i, c in enumerate(CLASS_NAMES, 1):
                    H1[c].append(int((l1 == i).sum())); H2[c].append(int((second[k][1] == i).sum()))
                    Yc[c].append(int((pr["labels"] == i).sum()))
        hh = {c: agreement_bundle(H2[c], H1[c]) for c in CLASS_NAMES if len(H1[c]) > 3}
        # model vs annotator-2 on the same subset, so comparison is like-for-like
        mm = {c: agreement_bundle(Yc[c], H2[c]) for c in CLASS_NAMES if len(H1[c]) > 3}
        R["human_vs_human"] = hh; R["model_vs_ann2"] = mm
        rows = []
        for c in hh:
            rows.append(f"{c} & {f(hh[c]['icc21'])} & {f(hh[c]['ba']['bias'])} & "
                        f"[{f(hh[c]['ba']['loa_lo'],1)}, {f(hh[c]['ba']['loa_hi'],1)}] & "
                        f"{f(hh[c]['mape'],1)} & {f(mm[c]['icc21'])} & [{f(mm[c]['ba']['loa_lo'],1)}, {f(mm[c]['ba']['loa_hi'],1)}] & {f(mm[c]['mape'],1)} " + r"\\")
        write(os.path.join(a.out, "table_human_baseline.tex"), "\n".join(rows))
        print("human-vs-human n =", len(H1[CLASS_NAMES[0]]))
        for c in hh:
            print(f"   {c}: human ICC={hh[c]['icc21']:.3f} MAPE={hh[c]['mape']:.1f}% | "
                  f"model ICC={mm[c]['icc21']:.3f} MAPE={mm[c]['mape']:.1f}%")
    else:
        print("\n[skip D] provide --second_annotator_dir to get the human-vs-human baseline "
              "(THIS IS THE KEY TABLE for the 'better than a human' claim)")

    # -------- C. Repeatability CV% ------------------------------------------
    if "repeat" not in a.skip:
        section("C. Repeatability CV%")
        cvres = {}
        if a.fields_dir and os.path.exists(a.fields_dir):
            fl = sorted(sum([glob.glob(os.path.join(a.fields_dir, f"*.{e}")) for e in ("jpg", "png", "jpeg")], []))
            cnts = {c: [] for c in CLASS_NAMES}
            for ip in fl:
                p = yolo(cv2.imread(ip))
                for i, c in enumerate(CLASS_NAMES, 1):
                    cnts[c].append(int(np.sum(p["labels"] == i)))
            cvres["A_field_to_field"] = {c: dict(mean=float(np.mean(v)), sd=float(np.std(v, ddof=1)),
                                                  cv=cv_percent(v),
                                                  cv_ci=boot_ci(cv_percent, v), n=len(v)) for c, v in cnts.items()}
            print("Protocol A:", {c: round(cvres['A_field_to_field'][c]['cv'], 1) for c in CLASS_NAMES})
        else:
            print("[skip A] --fields_dir not given (10-20 fields of ONE slide)")
        # Protocol B on up to 10 clinical images
        if clin:
            sel = clin[:10]; per_img = []
            for ip, _, _ in sel:
                img = cv2.imread(ip); cc = {c: [] for c in CLASS_NAMES}
                for _ in range(20):
                    p = yolo(perturb_small(img))
                    for i, c in enumerate(CLASS_NAMES, 1):
                        cc[c].append(int(np.sum(p["labels"] == i)))
                per_img.append({c: cv_percent(v) for c, v in cc.items()})
            cvres["B_perturbation"] = {c: dict(median_cv=float(np.nanmedian([d[c] for d in per_img])),
                                                iqr=[float(np.nanpercentile([d[c] for d in per_img], 25)),
                                                     float(np.nanpercentile([d[c] for d in per_img], 75))])
                                       for c in CLASS_NAMES}
            print("Protocol B (median CV%):", {c: round(cvres['B_perturbation'][c]['median_cv'], 1) for c in CLASS_NAMES})
        R["repeatability"] = cvres
        rows = []
        for c in CLASS_NAMES:
            A = cvres.get("A_field_to_field", {}).get(c); B = cvres.get("B_perturbation", {}).get(c)
            rows.append(f"{c} & {f(A['cv'],1) if A else '--'} & {ci(A['cv_ci'],1) if A else '--'} & "
                        f"{f(B['median_cv'],1) if B else '--'} " + r"\\")
        write(os.path.join(a.out, "table_cv.tex"), "\n".join(rows))

    # -------- E. Calibration ------------------------------------------------
    if "calib" not in a.skip and predcache:
        section("E. Calibration")
        cal = {}
        for name in predcache:
            cal[name] = calibration(*predcache[name])
            if cal[name]:
                print(f"ECE {name}: {cal[name]['ece']:.4f}")
                macro(f"ECE{name}", f"{cal[name]['ece']:.3f}")
        R["calibration"] = cal
        fig_reliability(cal, os.path.join(a.out, "fig_reliability.pdf"))

    # -------- F. Robustness -------------------------------------------------
    if "robust" not in a.skip and clin:
        section("F. Robustness curves (on clinical set, F1 + count MAPE for RBC/WBC)")
        sub = clin[: min(30, len(clin))]
        curves = {}
        for cname, fn in CORRUPTIONS.items():
            curves[cname] = []
            for sev in range(5):
                preds, gts = run_model(yolo, sub, preprocess=lambda im, fn=fn, sev=sev: fn(im, sev))
                det = detection_metrics(preds, gts)
                curves[cname].append(dict(mAP=det["mAP50"], f1_wbc=det["WBC"]["f1"], f1_rbc=det["RBC"]["f1"]))
            print(f"  {cname}: mAP", [round(x['mAP'], 3) for x in curves[cname]])
        R["robustness"] = curves
        fig, ax = plt.subplots(figsize=(3.4, 2.7))
        for cname, v in curves.items():
            ax.plot(range(5), [x["mAP"] for x in v], "o-", ms=3, lw=1, label=cname)
        ax.set_xlabel("corruption severity (0 = clean)"); ax.set_ylabel("mAP@0.5")
        ax.set_xticks(range(5)); ax.grid(alpha=.3); ax.legend(); fig.tight_layout()
        fig.savefig(os.path.join(a.out, "fig_robustness.pdf")); plt.close(fig)

    # -------- G. Quantisation ----------------------------------------------
    if "quant" not in a.skip and clin:
        section("G. Quantisation trade-off")
        variants = {"PyTorch FP32": ("pt", a.weights), "ONNX FP32": ("onnx", a.onnx_fp32),
                    "ONNX FP16": ("onnx", a.onnx_fp16), "ONNX INT8": ("onnx", a.onnx_int8)}
        qres = {}
        for vn, (kind, path) in variants.items():
            if not path or not os.path.exists(path):
                print(f"  [skip {vn}] not found: {path}"); continue
            m = yolo if kind == "pt" else YoloONNX(path, a.conf)
            lat = []
            img0 = cv2.imread(clin[0][0])
            for _ in range(3): m(img0)
            preds, gts = [], []
            for ip, b, l in clin:
                im = cv2.imread(ip); t0 = time.perf_counter(); p = m(im)
                lat.append((time.perf_counter() - t0) * 1000); preds.append(p); gts.append(dict(boxes=b, labels=l))
            det = detection_metrics(preds, gts); P, G = counts_from(preds, gts)
            qres[vn] = dict(size_mb=os.path.getsize(path) / 1e6, lat_ms=float(np.median(lat)),
                            lat_p95=float(np.percentile(lat, 95)), mAP50=det["mAP50"],
                            wbc_f1=det["WBC"]["f1"], rbc_mape=agreement_bundle(P["RBC"], G["RBC"])["mape"],
                            wbc_mape=agreement_bundle(P["WBC"], G["WBC"])["mape"])
            print(f"  {vn}: {qres[vn]}")
        R["quantisation"] = qres
        rows = [f"{k} & {f(v['size_mb'],1)} & {f(v['lat_ms'],0)} & {f(v['mAP50'],3)} & {f(v['wbc_f1'],3)} & "
                f"{f(v['rbc_mape'],1)} & {f(v['wbc_mape'],1)} " + r"\\" for k, v in qres.items()]
        write(os.path.join(a.out, "table_quant.tex"), "\n".join(rows))
        print("  NOTE: latency above is measured on THIS machine. Re-run on the Raspberry Pi for the paper.")

    # -------- H. SSDLite comparison ----------------------------------------
    if "ssd" not in a.skip and clin and os.path.exists(a.ssd_weights):
        section("H. SSDLite vs YOLOv8n")
        try:
            ssd = SSDLitePT(a.ssd_weights, a.conf)
            preds, gts = run_model(ssd, clin); det = detection_metrics(preds, gts)
            P, G = counts_from(preds, gts)
            R["ssd_clinical"] = dict(det=det, agree={c: agreement_bundle(P[c], G[c]) for c in CLASS_NAMES})
            print("SSDLite mAP50:", round(det["mAP50"], 3))
        except Exception as e:
            print("  SSDLite failed:", e)

    # -------- I. Domain adaptation experiments ------------------------------
    if "tune" not in a.skip and clin and len(clin) >= 20:
        section("I. Domain shift mitigation (fit on half of the 72, test on the other half)")
        idx = RNG.permutation(len(clin)); half = len(clin) // 2
        cal_items = [clin[i] for i in idx[:half]]; test_items = [clin[i] for i in idx[half:]]

        def stain_norm(img, ref=None):
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
            m, s = lab.mean((0, 1)), lab.std((0, 1)) + 1e-6
            tm, ts = REF_STATS
            return cv2.cvtColor(np.clip((lab - m) * (ts / s) + tm, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)

        if bccd:
            ref_l = [cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2LAB).astype(np.float32) for p, _, _ in bccd[:40]]
            REF_STATS = (np.mean([x.mean((0, 1)) for x in ref_l], 0), np.mean([x.std((0, 1)) for x in ref_l], 0))
        else:
            REF_STATS = (np.array([148.5, 142.3, 118.4]), np.array([32.4, 18.2, 14.1]))

        res = {}
        for tag, prep in (("baseline", None), ("stain_norm", stain_norm)):
            preds, gts = run_model(yolo, test_items, preprocess=prep)
            det = detection_metrics(preds, gts); P, G = counts_from(preds, gts)
            res[tag] = dict(mAP50=det["mAP50"], **{f"{c}_mape": agreement_bundle(P[c], G[c])["mape"] for c in CLASS_NAMES},
                            **{f"{c}_r": agreement_bundle(P[c], G[c])["pearson_r"] for c in CLASS_NAMES})
        # confidence-threshold sweep chosen on the calibration half
        best = (None, -1)
        for th in (0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5):
            preds, gts = run_model(yolo, cal_items, conf=th, preprocess=stain_norm)
            m = detection_metrics(preds, gts)["mAP50"]
            f1m = np.mean([detection_metrics(preds, gts)[c]["f1"] for c in CLASS_NAMES])
            if f1m > best[1]:
                best = (th, f1m)
        preds, gts = run_model(yolo, test_items, conf=best[0], preprocess=stain_norm)
        det = detection_metrics(preds, gts); P, G = counts_from(preds, gts)
        res["stain_norm+tuned_conf"] = dict(conf=best[0], mAP50=det["mAP50"],
                                             **{f"{c}_mape": agreement_bundle(P[c], G[c])["mape"] for c in CLASS_NAMES},
                                             **{f"{c}_r": agreement_bundle(P[c], G[c])["pearson_r"] for c in CLASS_NAMES})
        R["domain_shift"] = res
        for k, v in res.items():
            print(" ", k, {kk: round(vv, 3) for kk, vv in v.items()})
        rows = [f"{k.replace('_', ' ')} & {f(v['mAP50'],3)} & {f(v['RBC_mape'],1)} & {f(v['WBC_mape'],1)} & "
                f"{f(v['RBC_r'],2)} & {f(v['WBC_r'],2)} " + r"\\" for k, v in res.items()]
        write(os.path.join(a.out, "table_domain.tex"), "\n".join(rows))

    # -------- save ----------------------------------------------------------
    def clean(o):
        if isinstance(o, dict): return {k: clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)): return [clean(v) for v in o]
        if isinstance(o, (np.floating,)): return float(o)
        if isinstance(o, (np.integer,)): return int(o)
        if isinstance(o, float) and not np.isfinite(o): return None
        return o
    json.dump(clean(R), open(os.path.join(a.out, "results.json"), "w"), indent=2)
    write(os.path.join(a.out, "paper_numbers.tex"), "\n".join(macros) + "\n")
    print(f"\nDONE. Everything is in ./{a.out}/  -> zip that folder and send it back.")


if __name__ == "__main__":
    main()