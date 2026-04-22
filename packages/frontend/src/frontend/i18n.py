from __future__ import annotations


RUN_STATUS_LABELS = {
    None: 'ожидание',
    'created': 'создан',
    'scheduled': 'запланирован',
    'running': 'выполняется',
    'stopping': 'останавливается',
    'stopped': 'остановлен',
    'finished': 'завершен',
    'failed': 'ошибка',
}

SOURCE_TYPE_LABELS = {
    'file': 'файл',
    'webcam': 'веб-камера',
    'camera': 'камера',
}

PREVIEW_SOURCE_LABELS = {
    'backend': 'сервер',
    'local': 'локально',
}

DETECTION_LABELS = {
    'weapon': 'оружие',
    'gun': 'пистолет',
    'handgun': 'пистолет',
    'pistol': 'пистолет',
    'firearm': 'огнестрельное оружие',
    'rifle': 'винтовка',
    'shotgun': 'ружье',
    'knife': 'нож',
    'blade': 'лезвие',
    'grenade': 'граната',
}

BACKEND_DETAIL_TRANSLATIONS = {
    'Test run is already running': 'Обработка уже запущена.',
    'Only test runs with status "created" can be executed': (
        'Запустить можно только обработку в статусе "создан".'
    ),
    'Test run is not active': 'Обработка сейчас не активна.',
    'Only scheduled or running test runs can be stopped': (
        'Остановить можно только запланированную или выполняемую обработку.'
    ),
    'sample_every must be greater than 0': 'Параметр sample_every должен быть больше 0.',
    'backend returned an error': 'сервер вернул ошибку',
}


def translate_run_status(status: str | None) -> str:
    return RUN_STATUS_LABELS.get(status, status or 'неизвестно')


def translate_source_type(source_type: str) -> str:
    normalized = source_type.strip().lower()
    return SOURCE_TYPE_LABELS.get(normalized, source_type)


def translate_preview_state(connected: bool) -> str:
    return 'в сети' if connected else 'не в сети'


def translate_preview_source(mode: str | None) -> str:
    return PREVIEW_SOURCE_LABELS.get(mode, 'неизвестно')


def translate_detection_label(label: str | None) -> str:
    if not label:
        return 'опасный предмет'

    normalized = label.strip().lower().replace('-', ' ').replace('_', ' ')
    return DETECTION_LABELS.get(normalized, label)


def translate_backend_detail(detail: str) -> str:
    translated = detail
    for english, russian in BACKEND_DETAIL_TRANSLATIONS.items():
        translated = translated.replace(english, russian)
    return translated


def build_detection_alert_message(
    *,
    camera_name: str,
    label: str | None = None,
    score: float | int | None = None,
) -> str:
    details = [f'На камере "{camera_name}" подтверждено обнаружение опасного предмета.']

    translated_label = translate_detection_label(label)
    if translated_label:
        details.append(f'Метка: {translated_label}.')

    if isinstance(score, (float, int)):
        details.append(f'Уверенность модели: {float(score):.2f}.')

    return ' '.join(details)


def build_detection_event_summary(
    *,
    camera_name: str,
    label: str | None = None,
    score: float | int | None = None,
) -> str:
    translated_label = translate_detection_label(label)
    if isinstance(score, (float, int)):
        return (
            f'Камера "{camera_name}": обнаружен опасный предмет '
            f'({translated_label}, {float(score):.2f}).'
        )
    return f'Камера "{camera_name}": обнаружен опасный предмет ({translated_label}).'
