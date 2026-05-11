import pandas as pd
import matplotlib.pyplot as plt


def get_padded_limits(values, pad=0.05):
    '''
    Возвращает границы оси Y с небольшим отступом.

    Parameters
    ----------
    values : pandas.Series
        Значения, по которым нужно определить границы.
    pad : float
        Доля отступа сверху и снизу.

    Returns
    -------
    tuple[float, float]
        Нижняя и верхняя границы оси Y.
    '''
    min_value = float(values.min())
    max_value = float(values.max())

    span = max_value - min_value
    if span == 0:
        span = 1.0

    return min_value - span * pad, max_value + span * pad


# Путь к файлу с результатами обучения
csv_path = 'packages/ml/src/ml/inference/models/detect/train/results.csv'

df = pd.read_csv(csv_path).iloc[:50].copy()

columns = [
    'train/box_loss',
    'train/cls_loss',
    'train/dfl_loss',
    'metrics/precision(B)',
    'metrics/recall(B)',
    'val/box_loss',
    'val/cls_loss',
    'val/dfl_loss',
    'metrics/mAP50(B)',
    'metrics/mAP50-95(B)',
]

# Сброс стиля matplotlib, чтобы график был как стандартный Ultralytics results.png
plt.rcdefaults()

fig, axes = plt.subplots(2, 5, figsize=(22, 11), dpi=100)
axes = axes.ravel()

# Если в CSV есть колонка epoch, используем её
x = df['epoch'] if 'epoch' in df.columns else range(1, len(df) + 1)

for column_id, column in enumerate(columns):
    ax = axes[column_id]

    y = df[column]
    smooth = y.rolling(window=5, min_periods=1).mean()

    ax.plot(
        x,
        y,
        color='#1f77b4',
        marker='o',
        markersize=4,
        linewidth=3,
        label='results',
    )

    ax.plot(
        x,
        smooth,
        color='#ff7f0e',
        linestyle=':',
        linewidth=3,
        label='smooth',
    )

    ax.set_title(column, fontsize=24)
    ax.tick_params(axis='both', labelsize=12)

    # Легенда как в стандартном results.png — только на train/cls_loss
    if column == 'train/cls_loss':
        ax.legend(fontsize=18, loc='upper right')

fig.tight_layout()

plt.show()

