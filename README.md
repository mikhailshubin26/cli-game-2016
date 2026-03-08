# CLI-GEOPOLITIC
«Хорошая игра — это не просто набор механик и пикселей. Это метафизическое пространство, в котором игрок перестаёт быть обывателем позднего модерна и становится субъектом судьбы. В ней раскрывается воля, архетип, борьба порядка и хаоса. Настоящая игра — это маленькая война за смысл, где каждое действие игрока есть акт утверждения своей онтологической позиции в цифровом космосе.» — А.Г. Дугин

### процесс игры:
вы пришли ко власти. за окном только наступил 2016 год. оставьте свой след мировой истории и продержитесь хотя бы 15 минут, не скидывая ни на кого бомбу

### скачать:

macOS / Linux:
```commandline
git clone https://github.com/mikhailshubin26/cli-game-2016.git
cd cli-game-2016
python3 -m venv venv
source venv/bin/activate
pip3 install openai python-dotenv
touch .env
```

Windows:
```commandline
git clone https://github.com/mikhailshubin26/cli-game-2016.git
cd cli-game-2016
py -m venv venv
venv\Scripts\activate
pip install openai python-dotenv
type nul > .env
```

.env content:
```
DEEPSEEK_API_KEY=<api>
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

### запуск
macOS / Linux: `python3 game.py`
Windows: `py game.py`

### планируемые обновления:
* React версия игры
* Выбор уровня сложности
* Работа с сохранениями

### контакты:
* твиттер — https://x.com/mikleshubin
* почта — mailto:mishaelshubin@gmail.com

### поддержать
BTC: bc1qllfd0zxmk45j3x53d5dnu9y0ls7vdx60yyk3u4
ETH: 0x480468BbB77ef4a4abed20e81656e4CFBcc1C055
Tether USDT TRC20: 0x480468BbB77ef4a4abed20e81656e4CFBcc1C055
