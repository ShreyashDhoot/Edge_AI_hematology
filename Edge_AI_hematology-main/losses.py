import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
except ImportError:
    torch = None
    nn = object
    F = None

class AlphaBalancedFocalLoss(nn.Module if torch else object):
    def __init__(self, alpha=None, gamma=2.0, reduction="mean"):
        if torch:
            super().__init__()
        self.gamma = gamma
        self.reduction = reduction
        if alpha is None and torch is not None:
            self.alpha = torch.tensor([0.05, 0.2, 2.5, 1.2])
        else:
            self.alpha = alpha

    def forward(self, inputs, targets):
        if torch is None:
            raise RuntimeError("PyTorch required for FocalLoss.")
        ce_loss = F.cross_entropy(inputs, targets, reduction="none")
        pt = torch.exp(-ce_loss)
        if self.alpha is not None:
            if self.alpha.device != inputs.device:
                self.alpha = self.alpha.to(inputs.device)
            at = self.alpha[targets]
            focal_loss = at * ((1.0 - pt) ** self.gamma) * ce_loss
        else:
            focal_loss = ((1.0 - pt) ** self.gamma) * ce_loss
        return focal_loss.mean() if self.reduction == "mean" else focal_loss.sum()

def calculate_ciou(box1, box2):
    x1, y1 = np.maximum(box1[..., 0], box2[..., 0]), np.maximum(box1[..., 1], box2[..., 1])
    x2, y2 = np.minimum(box1[..., 2], box2[..., 2]), np.minimum(box1[..., 3], box2[..., 3])
    inter = np.maximum(0.0, x2 - x1) * np.maximum(0.0, y2 - y1)
    a1 = (box1[..., 2] - box1[..., 0]) * (box1[..., 3] - box1[..., 1])
    a2 = (box2[..., 2] - box2[..., 0]) * (box2[..., 3] - box2[..., 1])
    union = a1 + a2 - inter + 1e-7
    iou = inter / union
    ex1, ey1 = np.minimum(box1[..., 0], box2[..., 0]), np.minimum(box1[..., 1], box2[..., 1])
    ex2, ey2 = np.maximum(box1[..., 2], box2[..., 2]), np.maximum(box1[..., 3], box2[..., 3])
    c_diag_sq = (ex2 - ex1) ** 2 + (ey2 - ey1) ** 2 + 1e-7
    c1x, c1y = (box1[..., 0] + box1[..., 2]) / 2.0, (box1[..., 1] + box1[..., 3]) / 2.0
    c2x, c2y = (box2[..., 0] + box2[..., 2]) / 2.0, (box2[..., 1] + box2[..., 3]) / 2.0
    rho_sq = (c1x - c2x) ** 2 + (c1y - c2y) ** 2
    w1, h1 = np.maximum(1e-6, box1[..., 2] - box1[..., 0]), np.maximum(1e-6, box1[..., 3] - box1[..., 1])
    w2, h2 = np.maximum(1e-6, box2[..., 2] - box2[..., 0]), np.maximum(1e-6, box2[..., 3] - box2[..., 1])
    v = (4.0 / (np.pi ** 2)) * np.power(np.arctan(w2 / h2) - np.arctan(w1 / h1), 2)
    alpha = v / (1.0 - iou + v + 1e-7)
    return iou - (rho_sq / c_diag_sq) - (alpha * v)
