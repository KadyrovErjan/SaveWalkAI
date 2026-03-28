<div align="center">

# 🦯 SaveWalk AI

### Навигационный ассистент для слабовидящих

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![YOLO26n](https://img.shields.io/badge/YOLO26n-Custom%20Model-7B2FBE?style=flat-square&logo=python)](https://ultralytics.com)[![OpenCV](https://img.shields.io/badge/OpenCV-4.13-5C3EE8?style=flat-square&logo=opencv)](https://opencv.org)
[![ByteTrack](https://img.shields.io/badge/Tracker-ByteTrack-FF6B35?style=flat-square)]()
[![License](https://img.shields.io/badge/License-MIT-22C55E?style=flat-square)](LICENSE)
[![Version](https://img.shields.io/badge/Version-2.0-EF4444?style=flat-square)]()

**Система не просто описывает объекты — она помогает двигаться.**

Анализирует окружение через камеру в реальном времени и даёт чёткие голосовые команды:  
куда идти, где остановиться, как обойти препятствие.

</div>

---

## 📌 Что это такое

**SaveWalk AI** — локальная система помощи при ходьбе для людей с ограниченными возможностями зрения. Работает полностью офлайн, без интернета и без генерации речи. Только камера, мозг в виде YOLO и заранее записанные `.wav` файлы.

### Сравнение с обычной озвучкой

| Обычная система | SaveWalk AI |
|---|---|
| _"Человек, 1 метр, справа"_ | _"Идите левее"_ |
| _"Машина, 2 метра, слева"_ | _"Опасность, остановитесь"_ |
| _"Светофор красный"_ | _"Стоп"_ |
| Перечисляет всё подряд | Говорит только важное |
| Описывает картину | Ведёт человека |

---

## 🧠 Как это работает

```
📷 Камера
    │
    ▼
🔍 YOLO + ByteTrack ──────── обнаружение объектов + трекинг по track_id
    │
    ▼
📏 Расстояние (Pinhole) ───── дистанция по ширине bounding box
    │
    ▼
📉 EMA Сглаживание ────────── убирает резкие скачки (0.7→1.0→0.8 → плавно)
    │
    ▼
🧭 Направление + Движение ─── left/center/right + approaching/leaving/stable
    │
    ▼
⚠️ Risk Score ──────────────── car=10, bus=10, moto=9, bicycle=6, person=3
    │
    ▼
🎯 Top Threat ──────────────── выбор одного самого опасного объекта
    │
    ▼
🧩 Навигационная логика ────── stop / left / right / go / person_ahead
    │
    ▼
🔊 Воспроизведение .wav ────── один звук, cooldown, без повторов
```

---

## 🔊 Логика голосовых команд

Система выбирает **одну команду** по приоритету:

```
Приоритет   Ситуация                                   Команда
──────────────────────────────────────────────────────────────────────
    1       Любой объект ближе 1.0м                  🔴 stop.wav
    2       Транспорт приближается, dist < 2.5м       ↙ left.wav / right.wav
    3       Человек по центру + approaching < 2.0м   ⚠ person_ahead.wav
    4       Любое препятствие по центру < 3.5м        ↙ left.wav / right.wav
    5       Путь свободен (раз в 5 секунд)           🟢 go.wav
```

### Примеры реальных ситуаций

```
Ситуация                                  Что говорит система
──────────────────────────────────────────────────────────────────────
Человек идёт навстречу по центру      →   "Человек впереди" → "Правее"
Машина приближается слева             →   "Препятствие"
Объект вплотную (< 1м)                →   "Стоп"
Все стороны заняты                    →   "Нет прохода"
Путь свободен 5+ секунд               →   "Идите прямо"
Светофор переключился на зелёный      →   "Зелёный"
```

---

## 🏗️ Структура проекта

```
SaveWalkAI/
│
├── main.py                        # главный цикл
├── camera.py                      # захват кадров с камеры
├── sound_manager.py               # низкоуровневое воспроизведение .wav
│
├── core/
│   ├── detector.py                # YOLO + ByteTrack детекция
│   ├── distance.py                # расчёт расстояния (pinhole модель)
│   ├── tracker.py                 # EMA сглаживание, направление, движение
│   └── traffic_light.py          # определение цвета светофора (HSV)
│
├── services/
│   ├── danger_service.py          # risk score + pick_top_threat()
│   ├── navigation_service.py      # навигационные подсказки
│   └── sound_service.py          # логика выбора и воспроизведения звука
│
└── sounds/
    ├── system/                    # go.wav  stop.wav  left.wav  right.wav
    ├── obstacles/                 # person_ahead.wav  obstacle.wav  no_way.wav
    │                              # person_left.wav   person_right.wav
    ├── traffic/                   # red.wav  green.wav
    ├── road/                      # crosswalk.wav  intersection.wav
    └── warning/                   # danger.wav  very_close.wav
```

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

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
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

В `camera.py` измени индекс:

```python
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
# 0 = встроенная камера
# 1 = внешняя USB-камера
```

### Калибровка расстояния

В `core/distance.py`:

```python
FOCAL_LENGTH = 756   # подбери под свою камеру
```

**Как откалибровать точно:**

```
1. Встань ровно на 2.0м от камеры
2. Запусти main.py и посмотри в консоль:
   → person #1 | dist=0.9 | ...   (должно быть ~2.0)
3. Посчитай:
   FOCAL_LENGTH = (pixel_w_bbox × 2.0) / 0.45
4. Вставь результат в core/distance.py
```

### Пороги навигации

В `services/sound_service.py`:

```python
VERY_CLOSE_M  = 1.0   # ближе → немедленный stop
DANGER_DIST_M = 2.5   # транспорт приближается → предупреждение
PERSON_DIST_M = 2.0   # человек по центру → person_ahead
NAV_DIST_M    = 3.5   # объект по центру → предложить обход
COOLDOWN_SEC  = 2.5   # минимальный интервал между командами
GO_INTERVAL   = 5.0   # "go" не чаще раза в N сек
```

---

## 🖥️ Визуализация на экране

При запуске открывается окно с видео:

| Элемент | Значение |
|---|---|
| ⬜ Белая рамка | Top Threat — самый опасный объект в кадре |
| 🟥 Красная рамка | Объект ближе 3м |
| 🟩 Зелёная рамка | Объект дальше 3м (безопасно) |
| Цветная рамка TL | Цвет сигнала светофора (🔴🟡🟢) |

**Текст на рамке объекта:**
```
person #4   1.7m  center  approaching   r=9
  ↑ класс    ↑      ↑          ↑         ↑
           dist  direction  motion    risk score
```

---

## 📊 Пример вывода в консоль

```
15:10:49 [INFO] person #4  | dist=1.70 | dir=center | motion=approaching | risk=9.0
15:10:49 [INFO] [NAV] person_ahead.wav
15:10:52 [INFO] car #2     | dist=2.10 | dir=left   | motion=stable      | risk=10.0
15:10:55 [INFO] person #4  | dist=1.20 | dir=center | motion=approaching | risk=9.0
15:10:55 [INFO] [NAV] right.wav
15:10:58 [INFO] [TL] #11 red
```

---

## 📦 Технологии

| Библиотека | Назначение                             |
|---|----------------------------------------|
| `ultralytics` | YOLOv8 — детекция и трекинг объектов   |
| `opencv-python` | Захват видео с камеры и отрисовка      |
| `numpy` | Математика, HSV-анализ цвета светофора |
| `torch` | Backend для YOLO26n                    |
| `simpleaudio` / `pygame` / `winsound` | Воспроизведение `.wav` (авто-выбор)    |

Аудио бэкенд выбирается автоматически в порядке приоритета:  
`simpleaudio` → `pygame` → `winsound`

---

## 🔮 Планы на будущее

- [ ] Распознавание пешеходного перехода (`crosswalk.wav` уже готов)
- [ ] Распознавание перекрёстка (`intersection.wav` уже готов)
- [ ] Определение желтого сигнала светофора (`yellow.wav`)
- [ ] Ночной режим — усиление контраста при плохом освещении
- [ ] Поддержка Raspberry Pi 5 через ONNX-экспорт модели
- [ ] Мультиязычные звуки — кыргызский, русский, английский
- [ ] Адаптивный cooldown — меньше пауз при высоком риске
- [ ] Веб-интерфейс для настройки параметров без кода

---

## 👤 Автор

**Amin**  
г. Бишкек, Кыргызстан

Проект создан как практическая система помощи людям с ограниченными возможностями зрения на основе компьютерного зрения и искусственного интеллекта.

> *"Технологии должны служить людям — особенно тем, кому это нужно больше всего."*

---

## 📄 Лицензия

MIT License — свободно для личного и коммерческого использования.

Если проект оказался полезным — поставь ⭐ на GitHub.

---

<div align="center">

Сделано с ❤️ в Бишкеке · 2026

</div>