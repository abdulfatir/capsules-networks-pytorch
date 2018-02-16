import torch
import torch.nn.functional as F
import torch.nn as nn
from torch.autograd import Variable
from models.funcs import squash


class CapsNet(torch.nn.Module):
    def __init__(self):
        super(CapsNet, self).__init__()

        self.CUDA = torch.cuda.is_available()

        self.conv1 = torch.nn.Conv2d(1, 256, 9)
        self.conv2 = torch.nn.Conv2d(256, 256, 9, 2)
        self.W = torch.nn.Parameter(torch.randn(10, 32 * 6 * 6, 8, 16))
        self.decoder = nn.Sequential(
            nn.Linear(16 * 10, 512),
            nn.ReLU(inplace=True),
            nn.Linear(512, 1024),
            nn.ReLU(inplace=True),
            nn.Linear(1024, 784),
            nn.Sigmoid()
        )

    def forward(self, x, y=None):
        batch_size = x.size(0)
        x = F.relu(self.conv1(x), inplace=True)
        x = self.conv2(x)
        x = x.view((-1, 32 * 6 * 6, 8))
        x = squash(x)
        u_hat = torch.matmul(x[:, None, :, None, :], self.W[None, :, :, :, :])
        # u_hat.shape = batch_size x 10 x 1152 x 1 x 16
        if self.CUDA:
            b = Variable(torch.zeros(*u_hat.size())).cuda()
        else:
            b = Variable(torch.zeros(*u_hat.size()))

        for i in range(3):
            c = F.softmax(b, dim=2)
            v = squash((c * u_hat).sum(dim=2, keepdim=True))

            if i is not 2:
                db = (v * u_hat).sum(dim=-1, keepdim=True)
                # print(u_hat.shape, v.shape, b.shape, db.shape)
                b = b + db
        v = v.squeeze()
        class_probs = F.softmax(torch.sqrt((v ** 2).sum(dim=-1)), dim=-1)
        if y is not None:
            indices = y
        else:
            _, indices = torch.max(class_probs, dim=-1)
        if self.CUDA:
            mask = Variable(torch.eye(10)).cuda().index_select(dim=0, index=indices)
        else:
            mask = Variable(torch.eye(10)).index_select(dim=0, index=indices)
        recons = self.decoder((v * mask[:, :, None]).view(batch_size, -1))
        return class_probs, recons
