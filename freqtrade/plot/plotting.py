import logging
from typing import List

import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)


try:
    from plotly import tools
    from plotly.offline import plot
    import plotly.graph_objs as go
except ImportError:
    logger.exception("Module plotly not found \n Please install using `pip install plotly`")
    exit(1)


def generate_row(fig, row, indicators: List[str], data: pd.DataFrame) -> tools.make_subplots:
    """
    Generator all the indicator selected by the user for a specific row
    :param fig: Plot figure to append to
    :param row: row number for this plot
    :param indicators: List of indicators present in the dataframe
    :param data: candlestick DataFrame
    """
    for indicator in indicators:
        if indicator in data:
            # TODO: Figure out why scattergl causes problems
            scattergl = go.Scatter(
                x=data['date'],
                y=data[indicator].values,
                mode='lines',
                name=indicator
            )
            fig.append_trace(scattergl, row, 1)
        else:
            logger.info(
                'Indicator "%s" ignored. Reason: This indicator is not found '
                'in your strategy.',
                indicator
            )

    return fig


def plot_trades(fig, trades: pd.DataFrame):
    """
    Plot trades to "fig"
    """
    # Trades can be empty
    if trades is not None and len(trades) > 0:
        trade_buys = go.Scatter(
            x=trades["open_time"],
            y=trades["open_rate"],
            mode='markers',
            name='trade_buy',
            marker=dict(
                symbol='square-open',
                size=11,
                line=dict(width=2),
                color='green'
            )
        )
        # Create description for sell summarizing the trade
        desc = trades.apply(lambda row: f"{round(row['profitperc'], 3)}%, {row['sell_reason']}, "
                                        f"{row['duration']}min",
                            axis=1)
        trade_sells = go.Scatter(
            x=trades["close_time"],
            y=trades["close_rate"],
            text=desc,
            mode='markers',
            name='trade_sell',
            marker=dict(
                symbol='square-open',
                size=11,
                line=dict(width=2),
                color='red'
            )
        )
        fig.append_trace(trade_buys, 1, 1)
        fig.append_trace(trade_sells, 1, 1)
    else:
        logger.warning("No trades found.")
    return fig


def generate_graph(
    pair: str,
    data: pd.DataFrame,
    trades: pd.DataFrame = None,
    indicators1: List[str] = [],
    indicators2: List[str] = [],
) -> go.Figure:
    """
    Generate the graph from the data generated by Backtesting or from DB
    Volume will always be ploted in row2, so Row 1 and 3 are to our disposal for custom indicators
    :param pair: Pair to Display on the graph
    :param data: OHLCV DataFrame containing indicators and buy/sell signals
    :param trades: All trades created
    :param indicators1: List containing Main plot indicators
    :param indicators2: List containing Sub plot indicators
    :return: None
    """

    # Define the graph
    fig = tools.make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        row_width=[1, 1, 4],
        vertical_spacing=0.0001,
    )
    fig['layout'].update(title=pair)
    fig['layout']['yaxis1'].update(title='Price')
    fig['layout']['yaxis2'].update(title='Volume')
    fig['layout']['yaxis3'].update(title='Other')
    fig['layout']['xaxis']['rangeslider'].update(visible=False)

    # Common information
    candles = go.Candlestick(
        x=data.date,
        open=data.open,
        high=data.high,
        low=data.low,
        close=data.close,
        name='Price'
    )
    fig.append_trace(candles, 1, 1)

    if 'buy' in data.columns:
        df_buy = data[data['buy'] == 1]
        if len(df_buy) > 0:
            buys = go.Scatter(
                x=df_buy.date,
                y=df_buy.close,
                mode='markers',
                name='buy',
                marker=dict(
                    symbol='triangle-up-dot',
                    size=9,
                    line=dict(width=1),
                    color='green',
                )
            )
            fig.append_trace(buys, 1, 1)
        else:
            logger.warning("No buy-signals found.")

    if 'sell' in data.columns:
        df_sell = data[data['sell'] == 1]
        if len(df_sell) > 0:
            sells = go.Scatter(
                x=df_sell.date,
                y=df_sell.close,
                mode='markers',
                name='sell',
                marker=dict(
                    symbol='triangle-down-dot',
                    size=9,
                    line=dict(width=1),
                    color='red',
                )
            )
            fig.append_trace(sells, 1, 1)
        else:
            logger.warning("No sell-signals found.")

    if 'bb_lowerband' in data and 'bb_upperband' in data:
        bb_lower = go.Scattergl(
            x=data.date,
            y=data.bb_lowerband,
            name='BB lower',
            line={'color': 'rgba(255,255,255,0)'},
        )
        bb_upper = go.Scattergl(
            x=data.date,
            y=data.bb_upperband,
            name='BB upper',
            fill="tonexty",
            fillcolor="rgba(0,176,246,0.2)",
            line={'color': 'rgba(255,255,255,0)'},
        )
        fig.append_trace(bb_lower, 1, 1)
        fig.append_trace(bb_upper, 1, 1)

    # Add indicators to main plot
    fig = generate_row(fig=fig, row=1, indicators=indicators1, data=data)

    fig = plot_trades(fig, trades)

    # Volume goes to row 2
    volume = go.Bar(
        x=data['date'],
        y=data['volume'],
        name='Volume'
    )
    fig.append_trace(volume, 2, 1)

    # Add indicators to seperate row
    fig = generate_row(fig=fig, row=3, indicators=indicators2, data=data)

    return fig


def generate_plot_file(fig, pair, ticker_interval) -> None:
    """
    Generate a plot html file from pre populated fig plotly object
    :param fig: Plotly Figure to plot
    :param pair: Pair to plot (used as filename and Plot title)
    :param ticker_interval: Used as part of the filename
    :return: None
    """
    logger.info('Generate plot file for %s', pair)

    pair_name = pair.replace("/", "_")
    file_name = 'freqtrade-plot-' + pair_name + '-' + ticker_interval + '.html'

    Path("user_data/plots").mkdir(parents=True, exist_ok=True)

    plot(fig, filename=str(Path('user_data/plots').joinpath(file_name)),
         auto_open=False)
