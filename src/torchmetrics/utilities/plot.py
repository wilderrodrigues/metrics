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
from itertools import product
from math import ceil, floor, sqrt
from typing import Any, Generator, List, Optional, Sequence, Tuple, Union

import numpy as np
import torch
from torch import Tensor

from torchmetrics.utilities.imports import _LATEX_AVAILABLE, _MATPLOTLIB_AVAILABLE, _SCIENCEPLOT_AVAILABLE

if _MATPLOTLIB_AVAILABLE:
    import matplotlib
    import matplotlib.pyplot as plt

    _PLOT_OUT_TYPE = Tuple[plt.Figure, Union[matplotlib.axes.Axes, np.ndarray]]
    _AX_TYPE = matplotlib.axes.Axes

    style_change = plt.style.context
else:
    _PLOT_OUT_TYPE = Tuple[object, object]  # type: ignore[misc]
    _AX_TYPE = object

    from contextlib import contextmanager

    @contextmanager
    def style_change(*args: Any, **kwargs: Any) -> Generator:
        """Default no-ops decorator if matplotlib is not installed."""
        yield


if _SCIENCEPLOT_AVAILABLE:
    import scienceplots  # noqa: F401

    _style = ["science", "no-latex"]

_style = ["science"] if _SCIENCEPLOT_AVAILABLE and _LATEX_AVAILABLE else ["default"]


def _error_on_missing_matplotlib() -> None:
    """Raise error if matplotlib is not installed."""
    if not _MATPLOTLIB_AVAILABLE:
        raise ModuleNotFoundError(
            "Plot function expects `matplotlib` to be installed. Please install with `pip install matplotlib`"
        )


@style_change(_style)
def plot_single_or_multi_val(
    val: Union[Tensor, Sequence[Tensor]],
    ax: Optional[_AX_TYPE] = None,  # type: ignore[valid-type]
    higher_is_better: Optional[bool] = None,
    lower_bound: Optional[float] = None,
    upper_bound: Optional[float] = None,
    legend_name: Optional[str] = None,
    name: Optional[str] = None,
) -> _PLOT_OUT_TYPE:
    """Plot a single metric value or multiple, including bounds of value if existing.

    Args:
        val: A single tensor with one or multiple values (multiclass/label/output format) or a list of such tensors.
            If a list is provided the values are interpreted as a time series of evolving values.
        ax: Axis from a figure.
        higher_is_better: Indicates if a label indicating where the optimal value it should be added to the figure
        lower_bound: lower value that the metric can take
        upper_bound: upper value that the metric can take
        legend_name: for class based metrics specify the legend prefix e.g. Class or Label to use when multiple values
            are provided
        name: Name of the metric to use for the y-axis label

    Returns:
        A tuple consisting of the figure and respective ax objects of the generated figure

    Raises:
        ModuleNotFoundError:
            If `matplotlib` is not installed
    """
    _error_on_missing_matplotlib()
    fig, ax = plt.subplots() if ax is None else (None, ax)
    ax.get_xaxis().set_visible(False)

    if isinstance(val, Tensor):
        if val.numel() == 1:
            ax.plot([val.detach().cpu()], marker="o", markersize=10)
        else:
            for i, v in enumerate(val):
                label = f"{legend_name} {i}" if legend_name else f"{i}"
                ax.plot(i, v.detach().cpu(), marker="o", markersize=10, linestyle="None", label=label)
    else:
        val = torch.stack(list(val), 0)
        multi_series = val.ndim != 1
        val = val.T if multi_series else val.unsqueeze(0)
        for i, v in enumerate(val):
            label = (f"{legend_name} {i}" if legend_name else f"{i}") if multi_series else ""
            ax.plot(v.detach().cpu(), marker="o", markersize=10, linestyle="-", label=label)
        ax.get_xaxis().set_visible(True)
        ax.set_xlabel("Step")
        ax.set_xticks(torch.arange(val.shape[1]))

    handles, labels = ax.get_legend_handles_labels()
    if handles and labels:
        ax.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 1.15), ncol=3, fancybox=True, shadow=True)

    ylim = ax.get_ylim()
    if lower_bound is not None and upper_bound is not None:
        factor = 0.1 * (upper_bound - lower_bound)
    else:
        factor = 0.1 * (ylim[1] - ylim[0])

    ax.set_ylim(
        bottom=lower_bound - factor if lower_bound is not None else ylim[0] - factor,
        top=upper_bound + factor if upper_bound is not None else ylim[1] + factor,
    )

    ax.grid(True)
    ax.set_ylabel(name if name is not None else None)

    xlim = ax.get_xlim()
    factor = 0.1 * (xlim[1] - xlim[0])

    y_ = [lower_bound, upper_bound] if lower_bound or upper_bound else []
    ax.hlines(y_, xlim[0], xlim[1], linestyles="dashed", colors="k")
    if higher_is_better is not None:
        if lower_bound is not None and not higher_is_better:
            ax.set_xlim(xlim[0] - factor, xlim[1])
            ax.text(
                xlim[0], lower_bound, s="Optimal \n value", horizontalalignment="center", verticalalignment="center"
            )
        if upper_bound is not None and higher_is_better:
            ax.set_xlim(xlim[0] - factor, xlim[1])
            ax.text(
                xlim[0], upper_bound, s="Optimal \n value", horizontalalignment="center", verticalalignment="center"
            )
    return fig, ax


def _get_col_row_split(n: int) -> Tuple[int, int]:
    """Split `n` figures into `rows` x `cols` figures."""
    nsq = sqrt(n)
    if nsq * nsq == n:
        return int(nsq), int(nsq)
    if floor(nsq) * ceil(nsq) > n:
        return floor(nsq), ceil(nsq)
    return ceil(nsq), ceil(nsq)


def trim_axs(axs: Union[_AX_TYPE, np.ndarray], nb: int) -> np.ndarray:  # type: ignore[valid-type]
    """Reduce `axs` to `nb` Axes.

    All further Axes are removed from the figure.
    """
    if isinstance(axs, _AX_TYPE):
        return axs

    axs = axs.flat  # type: ignore[union-attr]
    for ax in axs[nb:]:
        ax.remove()
    return axs[:nb]


@style_change(_style)
def plot_confusion_matrix(
    confmat: Tensor,
    add_text: bool = True,
    labels: Optional[List[Union[int, str]]] = None,
) -> _PLOT_OUT_TYPE:
    """Plot an confusion matrix.

    Inspired by: https://github.com/scikit-learn/scikit-learn/blob/main/sklearn/metrics/_plot/confusion_matrix.py.
    Works for both binary, multiclass and multilabel confusion matrices.

    Args:
        confmat: the confusion matrix. Either should be an [N,N] matrix in the binary and multiclass cases or an
            [N, 2, 2] matrix for multilabel classification
        add_text: if text should be added to each cell with the given value
        labels: labels to add the x- and y-axis

    Returns:
        A tuple consisting of the figure and respective ax objects (or array of ax objects) of the generated figure

    Raises:
        ModuleNotFoundError:
            If `matplotlib` is not installed
    """
    _error_on_missing_matplotlib()

    if confmat.ndim == 3:  # multilabel
        nb, n_classes = confmat.shape[0], 2
        rows, cols = _get_col_row_split(nb)
    else:
        nb, n_classes, rows, cols = 1, confmat.shape[0], 1, 1

    if labels is not None and confmat.ndim != 3 and len(labels) != n_classes:
        raise ValueError(
            "Expected number of elements in arg `labels` to match number of labels in confmat but "
            f"got {len(labels)} and {n_classes}"
        )
    if confmat.ndim == 3:
        fig_label = labels or np.arange(nb)
        labels = list(map(str, range(n_classes)))
    else:
        fig_label = None
        labels = labels or np.arange(n_classes).tolist()

    fig, axs = plt.subplots(nrows=rows, ncols=cols)
    axs = trim_axs(axs, nb)
    for i in range(nb):
        ax = axs[i] if rows != 1 and cols != 1 else axs
        if fig_label is not None:
            ax.set_title(f"Label {fig_label[i]}", fontsize=15)
        ax.imshow(confmat[i].cpu().detach() if confmat.ndim == 3 else confmat.cpu().detach())
        ax.set_xlabel("True class", fontsize=15)
        ax.set_ylabel("Predicted class", fontsize=15)
        ax.set_xticks(list(range(n_classes)))
        ax.set_yticks(list(range(n_classes)))
        ax.set_xticklabels(labels, rotation=45, fontsize=10)
        ax.set_yticklabels(labels, rotation=25, fontsize=10)

        if add_text:
            for ii, jj in product(range(n_classes), range(n_classes)):
                val = confmat[i, ii, jj] if confmat.ndim == 3 else confmat[ii, jj]
                ax.text(jj, ii, str(val.item()), ha="center", va="center", fontsize=15)

    return fig, axs


@style_change(_style)
def plot_binary_roc_curve(
    tpr: Tensor,
    fpr: Tensor,
    ax: Optional[_AX_TYPE] = None,  # type: ignore[valid-type]
    roc_auc: Optional[Union[float, Tensor]] = None,
    name: Optional[str] = None,
    **kwargs: Any,
) -> _PLOT_OUT_TYPE:
    """Inspired by: https://github.com/scikit-learn/scikit-learn/blob/main/sklearn/metrics/_plot/roc_curve.py.

    Plots the roc curve

    Args:
        tpr: Tensor containing the values for True Positive Rate
        fpr: Tensor containing the values for False Positive Rate
        ax: Axis from a figure
        roc_auc: AUROC score (computed separately)
        name: Custom name to describe the classifier
        kwargs: additional keyword arguments for line drawing

    Returns:
        A tuple consisting of the figure and respective ax objects (or array of ax objects) of the generated figure

    Raises:
        ModuleNotFoundError:
            If `matplotlib` is not installed
    """
    _error_on_missing_matplotlib()
    fig, ax = plt.subplots() if ax is None else (None, ax)

    if isinstance(roc_auc, Tensor):
        assert roc_auc.numel() == 1, "roc_auc Tensor must consist of only one element"
        roc_auc = roc_auc.item()

    line_kwargs = {}
    if roc_auc is not None and name is not None:
        line_kwargs["label"] = f"{name} (AUC = {roc_auc:0.2f})"
    elif roc_auc is not None:
        line_kwargs["label"] = f"AUC = {roc_auc:0.2f}"
    elif name is not None:
        line_kwargs["label"] = name

    line_kwargs.update(**kwargs)

    ax.plot(fpr.detach().cpu(), tpr.detach().cpu(), **line_kwargs)
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")

    return fig, ax
