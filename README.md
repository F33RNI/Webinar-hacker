# Lecture-hacker (aka Webinar-hacker)
## Автоматическая запись и транскрибирование лекций из платформы webinar.ru или стороннего видео/аудио
<div style="width:100%;text-align:center;">
    <p align="center">
        <a href="https://github.com/F33RNI/Webinar-hacker/releases"><img alt="Download release" src="https://img.shields.io/badge/-Download%20latest-yellowgreen?style=for-the-badge&logo=github" ></a>
    </p>
    <p align="center">
        <a href="https://www.youtube.com/@F3RNI"><img alt="YouTube" src="https://img.shields.io/badge/-YouTube-red" ></a>
        <a href="https://f3rni.bandcamp.com"><img alt="Bandcamp" src="https://img.shields.io/badge/-Bandcamp-cyan" ></a>
        <a href="https://open.spotify.com/artist/22PQ62alehywlYiksbtzsm"><img alt="Spotify" src="https://img.shields.io/badge/-Spotify-green" ></a>
        <a href="https://soundcloud.com/f3rni"><img alt="SoundCloud" src="https://img.shields.io/badge/-SoundCloud-orange" ></a>
    </p>
</div>
<div style="width:100%;text-align:center;">
    <p align="center">
        <img src="Banner.jpg" width="auto" height="300">
    </p>
</div>

----------

## Надоело слушать бесполезные скучные лекции? Предоставь это Lecture-hacker и можешь идти спать! 😴

## Возможности

- Автоматический вход по ссылке с указанным именем, ожидание начала мероприятия
- Возможность нескольких ссылок (по завершении мероприятия автоматическое переключение на следующее)
- Вход, используя прокси
- Автоматическое написание приветственного сообщения в чат
- Автоматическое блокирование микрофона и камеры
- Автоматическое блокирование всплывающих окон и диалогов
- Автоматическое подтверждение присутствия
- Автоматическая активность путём периодического фокусирования на чате
- Автоматическая запись звука с возможностью задания порога чувствительности
- Автоматическое сохранение скриншотов
- Автоматическое переключение ссылок при превышении заданного времени ожидания
- Сборка скриншотов и аудио-фрагментов из стороннего видео-файла или аудио-файла
- Транскрибирование аудио в текст со знаками препинания при помощи локальной оффлайн-модели
- Разделение на параграфы по паузе
- Сопоставление скриншотов и транскрибированного текста в документ формата `.docx`
- Вычисление примерного оставшегося времени до окончания процесса транскрибирования

----------

## Как запустить и пользоваться

- Скачайте и распакуйте архив последней версии Lecture-hacker: https://github.com/F33RNI/Webinar-hacker/releases/latest
- Скачайте и установите Google Chrome, если у вас его нет: https://www.google.com/chrome/
- Запустите приложение, используя файл `Lecture-hacker.exe`

*Запись и сборка лекций всегда проходит в 2 этапа независимо от того, с Webinar она или из видео/аудио:*
1. *Непосредственно запись лекции. На этом этапе Lecture-hacker извлекает аудио-фрагменты в которых есть звук, по громкости превышающий установленный файл (каждый фрагмент записывается в отдельный WAV файл 16КГц PCM16 (signed int16)). А также следит за изменением изображения. Если изменения выше порога, сохраняется скриншот.*
2. *Из обработанных данных (набора .wav файлов и скриншотов) непосредственно собирается лекция. Для этого, в начале, аудио транскрибируется с сохранением времени, далее, текст вместе со скриншотами, согласно времени, записывается в .docx файл.*

### Вход и запись лекций на платформе Webinar
Основной функционал Lecture-hacker подразумевает автоматический вход по ссылке (и ожидание начала мероприятия), отправку приветственного сообщения в чат, симуляцию активности и запись лекции
- Для этого, перейдите на вкладку **Webinar**
- Вставьте ссылку на мероприятие в поле `Webinar links:`
- Если мероприятий несколько, нажмите на кнопку `+` чтобы добавить новую ссылку и на кнопки `-` чтобы удалить ссылки
- Укажите имя, с которым нужно подключиться в поле `Connect with name:`
- Укажите приветственное сообщение, которое необходимо отправить в чат после начала мероприятия в поле `Hello message:`
- Если требуется, укажите прокси в формате `IP:PORT` в поле `Proxy:`
- Укажите время, через которое нужно переключить / закрыть ссылку в полях `Max. link time:`. Если это не требуется, выставите 0 и 0
- Укажите, нужно ли записывать это мероприятие для последующего транскрибирования
- Нажмите кнопку `Start` и дождитесь открытия браузера
- Готово! Вход, запись и выход будут выполнены автоматически. Чтобы закрыть браузер раньше, нажмите на кнопку `Stop`

### Обработка стороннего видео- / аудио- файла
Перед сборкой лекции (транскрибированием), необходимо обработать видео- / аудио- файл.
- Для этого, перейдите на вкладку **Video / Audio file**
- Вставьте путь к файлу (или выберите файл при помощи кнопки `Browse`)
- Нажмите кнопку `Start` и дождитесь окончания обработки файла
- Файл можно закрыть в любой момент, нажав на кнопку `Stop`
- После обработки файла, можно транскрибировать данную лекцию

### Транскрибирование и сборка лекции в .docx - документ
После завершения мероприятия, записанный материал можно транскрибировать в `.docx` документ с картинками:
- Для этого обновите список записей нажав на кнопку `Refresh`
- Выберите из списка нужную запись
- Нажмите на кнопку `Build`. После окончания процесса, будет показано окно с путём сохранения конечного документа
- **Важно! Процесс сборки лекции может занимать длительное время! (может быть больше времени записанного материала) Не закрывайте приложение до разблокировки кнопок**
- Для ускорения процесса транскрибирования, установите CUDA 11.7: https://developer.nvidia.com/cuda-11-7-0-download-archive и убедитесь что при запуске сборки, внизу окна есть сообщение `Device: cuda`

----------

## Настройки и файл настроек

- Настройки Lecture-hacker хранятся в файле `settings.json`
- Настройки с префиксом `gui_` редактируются при помощи элементов интерфейса в реальном времени
- Для изменения других настроек, закройте приложение, откройте данный файл в текстовом редакторе, измените нужные параметры и откройте приложение заново
- **Важно! Lecture-hacker не проводит автоматическую проверку настроек. Если вы задали неверное значение, ошибка появится в неожиданный момент! Будьте внимательны при редактировании файла**

Текущий список настроек:
```json
{
    "screenshot_diff_threshold_percents": 5,
    "opencv_threshold": 10,
    "loop_interval_seconds": 3.0,
    "timestamp_format": "%d_%m_%Y__%H_%M_%S",
    "audio_chunk_size": 4096,
    "audio_recording_chunks_min": 5,
    "audio_wav_sampling_rate": 16000,
    "audio_wav_resampling_type": "soxr_mq",
    "paragraph_audio_distance_min_milliseconds": 5000,
    "recordings_directory_name": "recordings",
    "lectures_directory_name": "lectures",
    "audio_directory_name": "audio",
    "screenshots_directory_name": "screenshots",
    "whisper_model_name": "medium",
    "whisper_model_language": "ru",
    "lecture_build_time_filter_factor": 0.8,
    "lecture_picture_width_inches": 6.0,
    "lecture_font_size_pt": 12,
    "lecture_default_text_color": [
        0,
        0,
        0
    ],
    "lecture_low_confidence_text_color": [
        150,
        0,
        0
    ],
    "word_low_confidence_threshold_percents": 70,
    "save_lecture_to_directory": "",
    "gui_links": [],
    "gui_name": "Tester",
    "gui_hello_message": "\u0417\u0434\u0440\u0430\u0432\u0441\u0442\u0432\u0443\u0439\u0442\u0435!",
    "gui_hello_message_enabled": true,
    "gui_recording_enabled": true,
    "gui_proxy": "",
    "gui_max_event_time_enabled": true,
    "gui_max_event_time_milliseconds": 6000000,
    "gui_audio_threshold_dbfs": -35,
    "gui_video_audio_file": "",
    "gui_tabs_current_index": 0
}
```

----------

## Зависимости

- **whisper-timestamped**: https://github.com/linto-ai/whisper-timestamped
- **openai/whisper-medium**: https://huggingface.co/openai/whisper-medium
- Другие зависимости и пакеты, указанные в файле `requirements.txt`

----------

## Запуск из исходников / сборка из исходников

- Подробных инструкции пока неть 🙃
- Но можно попробовать склонировать репозиторий `git clone https://github.com/F33RNI/Webinar-hacker`
- Установить пакеты `pip install -r requirements.txt --upgrade`
- Установить CUDA 11.7
- Скачать файл `ffmpeg.exe` https://ffbinaries.com/downloads в папку с проектом 
- И попробовать запустить приложение `python main.py`

----------

## Участие в разработке

- Хотите добавить что-то новое / исправить баг? Создайте пул-реквест / issue!

----------

## P.S. Проект находится в стадии разработки!
