import torch
import torch.nn as nn
from qil import Quant_Conv2d, Quant_Activation
from torchsummary import summary


class BasicBlock(nn.Module):
    expansion = 1

    def __init__(self, in_planes, planes, stride=1, downsample=None, w_bits=32, a_bits=32):
        super(BasicBlock, self).__init__()

        self.quant_conv1 = Quant_Conv2d(in_planes, planes, 3, stride, padding=1, bits=w_bits)
        self.bn1 = nn.BatchNorm2d(planes)
        self.quant_activation_1 = Quant_Activation(a_bits)
        self.quant_conv2 = Quant_Conv2d(planes, planes, 3, padding=1, bits=w_bits)
        self.bn2 = nn.BatchNorm2d(planes)
        self.quant_activation_2 = Quant_Activation(a_bits)
        self.downsample = downsample
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):

        identity = x
        out = self.quant_conv1(x)
        out = self.bn1(out)
        out = self.relu(out)
        out = self.quant_activation_1(out)
        out = self.quant_conv2(out)
        out = self.bn2(out)

        if self.downsample is not None:
            identity = self.downsample(x)
        out += identity

        out = self.relu(out)
        out = self.quant_activation_2(out)

        return out


class ResNet(nn.Module):
    def __init__(self, block, layers, num_classes):
        super(ResNet, self).__init__()

        self.norm_layer = nn.BatchNorm2d

        self.in_planes = 16
        self.dilation = 1

        """ first Layer doesn't apply qantization """
        self.conv1 = nn.Conv2d(3, self.in_planes, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = self.norm_layer(self.in_planes)
        self.relu = nn.ReLU(inplace=True)
        # self.maxpooling = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)

        """ Quantization """
        self.layer1 = self._make_layer(block, 16, layers[0], stride=1)
        self.layer2 = self._make_layer(block, 32, layers[1], stride=2)
        self.layer3 = self._make_layer(block, 64, layers[2], stride=2)

        """ Average Pooling """
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))

        """ Final Layer doesn't apply quantization """
        self.fc = nn.Linear(64 * block.expansion, num_classes)

        # TODO
        """ Init Weight """

    def _make_layer(self, block, planes, layer, stride=None):

        downsample = None
        layers = []

        if stride != 1 or self.in_planes != planes * block.expansion:
            downsample = nn.Sequential(
                nn.Conv2d(self.in_planes, planes, 1, stride),
                nn.BatchNorm2d(planes * block.expansion)
            )
        layers.append(block(self.in_planes, planes, stride, downsample))
        
        self.in_planes = planes * block.expansion
        for num_block in range(1, layer):
            layers.append(block(self.in_planes, planes))

        return nn.Sequential(*layers)

    def _forward_impl(self, x):

        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)

        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)

        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.fc(x)

        return x

    def forward(self, x):
        return self._forward_impl(x)


if __name__ == '__main__':

    model = ResNet(BasicBlock, [3, 3, 3], 10)
    print(model)
    summary(model, (3, 32, 32), depth=3)
