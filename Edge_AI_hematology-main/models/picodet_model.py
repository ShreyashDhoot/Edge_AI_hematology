try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
except ImportError:
    torch = None
    nn = object

class DepthwiseSeparableConv(nn.Module if torch else object):
    def __init__(self, in_ch, out_ch, stride=1):
        if torch:
            super().__init__()
            self.dw = nn.Conv2d(in_ch, in_ch, kernel_size=3, stride=stride, padding=1, groups=in_ch, bias=False)
            self.bn1 = nn.BatchNorm2d(in_ch)
            self.pw = nn.Conv2d(in_ch, out_ch, kernel_size=1, bias=False)
            self.bn2 = nn.BatchNorm2d(out_ch)
            self.act = nn.Hardswish(inplace=True)

    def forward(self, x):
        return self.act(self.bn2(self.pw(self.act(self.bn1(self.dw(x))))))

class PicoDetSModel(nn.Module if torch else object):
    def __init__(self, num_classes=3):
        if torch:
            super().__init__()
            self.num_classes = num_classes
            self.stem = nn.Sequential(
                nn.Conv2d(3, 16, kernel_size=3, stride=2, padding=1, bias=False),
                nn.BatchNorm2d(16),
                nn.Hardswish(inplace=True)
            )
            self.s1 = DepthwiseSeparableConv(16, 32, stride=2)
            self.s2 = DepthwiseSeparableConv(32, 64, stride=2)
            self.s3 = DepthwiseSeparableConv(64, 128, stride=2)
            self.cls_head = nn.Conv2d(128, num_classes, 3, padding=1)
            self.reg_head = nn.Conv2d(128, 4, 3, padding=1)

    def forward(self, x):
        if torch is None:
            raise RuntimeError('PyTorch required.')
        feat = self.s3(self.s2(self.s1(self.stem(x))))
        return self.cls_head(feat), self.reg_head(feat)
