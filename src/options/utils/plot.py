import json
from typing import Iterable, Any, Callable

import websockets

DataSet = Any


def null(*_):
    return None


async def plot(
        data_sets: [Iterable[DataSet]],
        get_data: Callable[[DataSet], Iterable[Any]],
        get_x: Callable[[Any], float],
        get_y: Callable[[Any], float],
        get_x_label: Callable[[Any], float] = None,
        get_y_label: Callable[[Any], float] = None,
        get_dataset_label: Callable[[DataSet], str] = null,
        get_datum_label: Callable[[Any, DataSet], str] = null,
        stack_charts: bool = False,
        show_labels: bool = True,
        normalize: bool = True,
        scatter: bool = False
):
    _get_x_label = get_x_label or (lambda d: f'{get_x(d)}')
    _get_y_label = get_y_label or (lambda d: f'{get_y(d)}')
    data = dict(
        dataSets=[
            dict(
                label=get_dataset_label(data_set),
                data=[
                    dict(
                        x=dict(label=_get_x_label(d), value=get_x(d)),
                        y=dict(label=_get_y_label(d), value=get_y(d)),
                        label=get_datum_label(d, data_set)
                    ) for d in get_data(data_set)
                ]
            ) for data_set in data_sets
        ],
        options=dict(
            stackCharts=stack_charts,
            showLabels=show_labels,
            normalize=normalize,
            scatter=scatter
        )
    )
    async with websockets.connect('ws://options-server:8765') as websocket:
        await websocket.send(json.dumps(data))
