# Copyright The Lightning team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import torch
from pytorch_lightning import LightningModule
from torch.utils.data import Dataset


class RandomDictStringDataset(Dataset):
    """Class for creating a dictionary of random strings."""

    def __init__(self, size, length):
        self.len = length
        self.data = torch.randn(length, size)

    def __getitem__(self, index):
        """Get datapoint."""
        return {"id": str(index), "x": self.data[index]}

    def __len__(self):
        """Return length of dataset."""
        return self.len


class RandomDataset(Dataset):
    """Random dataset for testing PL Module."""

    def __init__(self, size, length):
        self.len = length
        self.data = torch.randn(length, size)

    def __getitem__(self, index):
        """Get datapoint."""
        return self.data[index]

    def __len__(self):
        """Get length of dataset."""
        return self.len


class BoringModel(LightningModule):
    """Testing PL Module.

    Use as follows:
    - subclass
    - modify the behavior for what you want

    class TestModel(BaseTestModel):
        def training_step(...):
            # do your own thing

    or:

    model = BaseTestModel()
    model.training_epoch_end = None
    """

    def __init__(self):
        super().__init__()
        self.layer = torch.nn.Linear(32, 2)

    def forward(self, x):
        return self.layer(x)

    @staticmethod
    def loss(_, prediction):
        # An arbitrary loss to have a loss that updates the model weights during `Trainer.fit` calls
        return torch.nn.functional.mse_loss(prediction, torch.ones_like(prediction))

    def step(self, x):
        x = self(x)
        return torch.nn.functional.mse_loss(x, torch.ones_like(x))

    def training_step(self, batch, batch_idx):
        output = self.layer(batch)
        loss = self.loss(batch, output)
        return {"loss": loss}

    @staticmethod
    def training_step_end(training_step_outputs):
        return training_step_outputs

    @staticmethod
    def training_epoch_end(outputs) -> None:
        torch.stack([x["loss"] for x in outputs]).mean()

    def validation_step(self, batch, batch_idx):
        output = self.layer(batch)
        loss = self.loss(batch, output)
        return {"x": loss}

    @staticmethod
    def validation_epoch_end(outputs) -> None:
        torch.stack([x["x"] for x in outputs]).mean()

    def test_step(self, batch, batch_idx):
        output = self.layer(batch)
        loss = self.loss(batch, output)
        return {"y": loss}

    @staticmethod
    def test_epoch_end(outputs) -> None:
        torch.stack([x["y"] for x in outputs]).mean()

    def configure_optimizers(self):
        optimizer = torch.optim.SGD(self.layer.parameters(), lr=0.1)
        lr_scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=1)
        return [optimizer], [lr_scheduler]

    @staticmethod
    def train_dataloader():
        return torch.utils.data.DataLoader(RandomDataset(32, 64))

    @staticmethod
    def val_dataloader():
        return torch.utils.data.DataLoader(RandomDataset(32, 64))

    @staticmethod
    def test_dataloader():
        return torch.utils.data.DataLoader(RandomDataset(32, 64))
