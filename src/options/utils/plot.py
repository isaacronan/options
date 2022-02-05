import json
from typing import Iterable, Any, Callable

import websockets

DataSet = Iterable[Any]


def null(*_):
    return None


async def plot(
        data_sets: [Iterable[DataSet]],
        get_data: Callable[[DataSet], Iterable[Any]],
        get_x: Callable[[Any], float],
        get_y: Callable[[Any], float],
        get_dataset_label: Callable[[DataSet], str] = null,
        get_datum_label: Callable[[Any], str] = null,
        stack_charts: bool = False,
        show_labels: bool = True,
        normalize: bool = True,
):
    data = dict(
        dataSets=[
            dict(
                label=get_dataset_label(data_set),
                data=[
                    dict(
                        x=get_x(d),
                        y=get_y(d),
                        label=get_datum_label(d)
                    ) for d in get_data(data_set)
                ]
            ) for data_set in data_sets
        ],
        options=dict(
            stackCharts=stack_charts,
            showLabels=show_labels,
            normalize=normalize,
        )
    )
    async with websockets.connect('ws://options-server:8765') as websocket:
        await websocket.send(json.dumps(data))
