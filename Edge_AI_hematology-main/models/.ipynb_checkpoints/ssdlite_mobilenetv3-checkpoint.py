try:
    import torch
    import torch.nn as nn
    from torchvision.models.detection import (
        ssdlite320_mobilenet_v3_large,
        SSDLite320_MobileNet_V3_Large_Weights,
    )
except ImportError:
    torch = None
    nn = object


def build_ssdlite_mobilenetv3(num_classes=4, pretrained=True):
    if torch is None:
        return None

    weights = (
        SSDLite320_MobileNet_V3_Large_Weights.DEFAULT
        if pretrained
        else None
    )

    # IMPORTANT:
    # weights_backbone=None forces torchvision's reduced-tail
    # MobileNetV3 configuration, matching the trained checkpoint.
    model = ssdlite320_mobilenet_v3_large(
        weights=weights,
        weights_backbone=None,
    )

    in_channels = [
        layer[0][0].in_channels
        for layer in model.head.classification_head.module_list
    ]

    from torchvision.models.detection.ssdlite import SSDLiteClassificationHead

    num_anchors = model.anchor_generator.num_anchors_per_location()

    model.head.classification_head = SSDLiteClassificationHead(
        in_channels=in_channels,
        num_anchors=num_anchors,
        num_classes=num_classes,
        norm_layer=nn.BatchNorm2d,
    )

    return model