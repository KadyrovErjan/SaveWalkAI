<div align="center">

# 🦯 SaveWalk AI

### Система компьютерного зрения для безопасной ходьбы

[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)](https://python.org)
[![YOLOv8](https://img.shields.io/badge/YOLO-v8n-purple?style=flat-square)](https://ultralytics.com)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green?style=flat-square&logo=opencv)](https://opencv.org)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![Version](https://img.shields.io/badge/Version-2.0-red?style=flat-square)]()

> Помогает людям с ограниченными возможностями зрения безопасно передвигаться в городской среде — обнаруживает объекты, оценивает опасность и сообщает голосом через готовые `.wav` файлы.

</div>

---

## 📌 Что это такое

**SaveWalk AI** — локальная real-time система, которая:

- 📷 захватывает видео с камеры
- 🧠 обнаруживает людей, машины, светофоры и другие объекты через **YOLOv8**
- 📏 оценивает расстояние до каждого объекта
- 🎯 определяет направление (слева / по центру / справа) и движение (приближается / удаляется)
- ⚠️ вычисляет уровень опасности и выбирает **самый опасный объект**
- 🔊 воспроизводит заранее записанные `.wav` файлы — без TTS, без интернета
- 🚦 распознаёт цвет светофора и озвучивает его

---

## 🏗️ Архитектура

```
SaveWalkAI/
│
├── main.py                        # главный цикл
├── camera.py                      # захват кадров с камеры
├── sound_manager.py               # низкоуровневое воспроизведение .wav
│
├── core/
│   ├── detector.py                # YOLO + ByteTrack детекция
│   ├── distance.py                # расчёт расстояния по bbox
│   ├── tracker.py                 # EMA сглаживание, направление, движение
│   └── traffic_light.py          # HSV-анализ цвета светофора
│
└── services/
    ├── danger_service.py          # risk score + приоритизация объектов
    ├── navigation_service.py      # навигационные подсказки
    └── sound_service.py          # логика воспроизведения звуков
```

### Поток данных

```
Камера → YOLO+ByteTrack → Расстояние → Сглаживание (EMA)
                                              ↓
                               Направление + Движение
                                              ↓
                                       Risk Score
                                              ↓
                                    Top Threat (1 объект)
                                              ↓
                              SoundService → play_sequence()
                                              ↓
                              direction.wav → dist.wav → motion.wav
```

---

## ✨ Возможности v2.0

| Функция | Описание |
|---|---|
| **EMA сглаживание** | Убирает резкие скачки расстояния (0.7→1.0→0.8 → плавная кривая) |
| **Направление** | Определяет `left / center / right` по положению bbox в кадре |
| **Движение** | Отслеживает `approaching / leaving / stable` за последние 1.5 сек |
| **Risk Score** | `car approaching at 1m` = риск 30, `person leaving at 4m` = риск 0.9 |
| **Приоритизация** | Озвучивается только **самый опасный** объект — без звуковой каши |
| **Навигация** | При препятствии по центру → `obstacle.wav → go_left.wav` |
| **Светофор** | Определяет красный / жёлтый / зелёный через HSV-анализ |
| **Cooldown** | Один объект озвучивается не чаще раза в 2.5 секунды |

---

## 🔊 Структура звуков

```
sounds/
│
├── person/
│   ├── dist/          1.wav  2.wav  3.wav  4.wav  5.wav
│   ├── direction/     left.wav  right.wav  center.wav
│   ├── motion/        approaching.wav  leaving.wav  stable.wav
│   └── alert/         danger.wav  very_close.wav
│
├── car/
│   ├── direction/     left.wav  right.wav  center.wav
│   ├── motion/        approaching.wav  leaving.wav  stable.wav
│   └── alert/         danger.wav  very_close.wav
│
├── navigation/
│   ├── go_left.wav
│   ├── go_right.wav
│   ├── go_straight.wav
│   └── obstacle.wav
│
├── alerts/            danger.wav  very_close.wav   ← fallback
│
└── traffic light/
    ├── red.wav
    ├── green.wav
    └── yellow.wav
```

### Логика воспроизведения

```
risk >= 15 (очень опасно)
  └─→  alert/very_close.wav   (если < 1.5м)
  └─→  alert/danger.wav       (иначе)

direction == center  AND  dist <= 2.5м
  └─→  navigation/obstacle.wav  →  go_left.wav / go_right.wav

обычный случай
  └─→  direction/left.wav  →  dist/2.wav  →  motion/approaching.wav
```

> Если файл не найден — он пропускается. Программа не падает.

---

## 🚀 Установка

### 1. Клонировать репозиторий

```bash
git clone https://github.com/yourname/SaveWalkAI.git
cd SaveWalkAI
```

### 2. Создать виртуальное окружение

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux / macOS
```

### 3. Установить зависимости

```bash
pip install -r req.txt
```

### 4. Запустить

```bash
python main.py
```

Нажми **Q** для выхода.

---

## ⚙️ Настройка

### Камера

В `camera.py` измени индекс камеры:

```python
cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)  # 0 = встроенная, 1 = USB
```

### Калибровка расстояния

В `core/distance.py`:

```python
FOCAL_LENGTH = 756   # подбери под свою камеру
```

**Как откалибровать:**
1. Встань ровно на **2 метра** от камеры
2. Запусти программу — в консоли увидишь `pixel_w` для person
3. Посчитай: `FOCAL_LENGTH = (pixel_w × 2.0) / 0.45`
4. Вставь результат

### Уровень риска

В `services/danger_service.py`:

```python
RISK_LEVEL = {
    "car":        10,
    "bus":        10,
    "motorcycle": 9,
    "bicycle":    6,
    "person":     3,
}
```

---

## 📊 Пример вывода в консоль

```
15:10:49 [INFO] person #4  | dist=1.70 | dir=center | motion=approaching | risk=9.0
15:10:52 [INFO] car #2     | dist=3.20 | dir=left   | motion=stable      | risk=15.0
15:10:52 [INFO] [SOUND] car #2 | risk=15.0 | seq=['left.wav', 'danger.wav']
15:10:55 [INFO] [NAV] obstacle ahead 1.7m → move right
15:10:58 [INFO] [СВЕТОФОР] #11  red
```

---

## 🖥️ Визуализация на экране

| Элемент | Описание |
|---|---|
| 🟥 Красная рамка | Объект ближе 3м |
| 🟩 Зелёная рамка | Объект дальше 3м |
| ⬜ Белая рамка | Top Threat — самый опасный объект |
| 🟦 Голубой текст | Навигационная подсказка |
| Рамка светофора | Меняет цвет по сигналу (красная / зелёная / жёлтая) |

---

## 🛠️ Зависимости

| Библиотека | Назначение |
|---|---|
| `ultralytics` | YOLOv8 детекция и трекинг |
| `opencv-python` | Захват видео и отрисовка |
| `numpy` | Математика и HSV-анализ |
| `torch` | Backend для YOLO |
| `simpleaudio` / `pygame` / `winsound` | Воспроизведение звука (авто-выбор) |

---

## 🗺️ Roadmap

- [ ] Поддержка дополнительных классов (велосипед, мотоцикл)
- [ ] Адаптивный порог опасности по времени суток
- [ ] Голосовые подсказки на нескольких языках
- [ ] Мобильная версия (Raspberry Pi / Android)
- [ ] Веб-интерфейс для настройки параметров

---

## 📄 Лицензия

MIT License — свободно для личного и коммерческого использования.

---

<div align="center">

Сделано с ❤️ для людей с ограниченными возможностями зрения

</div>