"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    🦊  FOX TERMINAL  —  DISCORD BOT  v3.0                   ║
║                                                                               ║
║  Terminal completo dentro do Discord — Google Colab Edition                  ║
║  Apenas membros com o cargo autorizado podem usar os comandos                ║
║                                                                               ║
║  SEM PREFIXO — use os comandos igual um terminal real:                       ║
║                                                                               ║
║  PYTHON       pip install / uninstall / list / show / freeze / search        ║
║  NODE         npm / npx / yarn / pnpm / bun                                  ║
║  SISTEMA      apt / apt-get / dpkg / snap                                    ║
║  TERMUX       pkg install / update / upgrade / search / list                 ║
║  RUST         cargo install / build / run / test / update                    ║
║  RUBY         gem install / uninstall / list / update                        ║
║  GO           go install / get / build / run / test                          ║
║  JAVA         mvn / gradle                                                    ║
║  PHP          composer require / install / update                             ║
║  GIT          clone / status / log / add / commit / push / pull / diff       ║
║  CANAIS       mkdir / ls / rm / cd / pwd / cat / echo / touch / mv / cp      ║
║  SHELL        env / export / ps / df / du / top / kill / chmod               ║
║  REDE         curl / wget / ping / netstat / ifconfig / nmap                 ║
║  INFO         whoami / uname / uptime / date / cal / history                 ║
║  EDITOR       nano / vim (simulado) / cat / head / tail / grep / wc          ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

# ══════════════════════════════════════════════════════════════════════════════
#  IMPORTS
# ══════════════════════════════════════════════════════════════════════════════
import discord
from discord.ext import commands, tasks
import asyncio
import subprocess
import sys
import os
import io
import re
import json
import time
import math
import random
import platform
import shutil
import textwrap
import threading
from datetime import datetime, timezone
from typing import Optional

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURAÇÕES GLOBAIS
# ══════════════════════════════════════════════════════════════════════════════
BOT_TOKEN           = os.environ.get('BOT_TOKEN')
CARGO_AUTORIZADO_ID = 1465895263582294271   # Apenas este cargo pode usar o bot
CATEGORIA_NOME      = "TERMINAL"            # Categoria onde mkdir cria canais
LOG_CANAL_NOME      = "fox-logs"            # Canal de logs (criado automaticamente)
MAX_OUTPUT_CHARS    = 3500                  # Limite de caracteres por embed
INSTALL_TIMEOUT     = 120                   # Timeout de instalações (segundos)
CMD_TIMEOUT         = 30                    # Timeout de comandos simples

# ── Cores dos embeds ──────────────────────────────────────────────────────────
COR_OK         = 0x2ECC71   # verde
COR_ERRO       = 0xE74C3C   # vermelho
COR_INFO       = 0x3498DB   # azul
COR_LOADING    = 0xF39C12   # laranja (loading)
COR_TERMINAL   = 0x1ABC9C   # ciano (terminal)
COR_AVISO      = 0xF1C40F   # amarelo
COR_ROXO       = 0x9B59B6   # roxo
COR_CINZA      = 0x95A5A6   # cinza
COR_PROIBIDO   = 0xC0392B   # vermelho escuro

# ── Emojis ────────────────────────────────────────────────────────────────────
E_FOX    = "🦊"
E_OK     = "✅"
E_ERR    = "❌"
E_LOAD   = "⏳"
E_PKG    = "📦"
E_FOLDER = "📁"
E_GIT    = "🔀"
E_PYTHON = "🐍"
E_NODE   = "🟢"
E_RUST   = "🦀"
E_RUBY   = "💎"
E_GO     = "🐹"
E_JAVA   = "☕"
E_PHP    = "🐘"
E_SYS    = "⚙️"
E_NET    = "🌐"
E_LOCK   = "🔒"
E_INFO   = "ℹ️"
E_TERM   = "💻"
E_FIRE   = "🔥"
E_CLOCK  = "🕐"
E_GRAPH  = "📊"
E_LOG    = "📋"
E_WARN   = "⚠️"
E_DB     = "🗄️"
E_SHIELD = "🛡️"
E_ROCKET = "🚀"
E_STAR   = "⭐"
E_GEAR   = "⚙️"
E_GLOBE  = "🌍"
E_DOCKER = "🐳"
E_KEY    = "🔑"

# ══════════════════════════════════════════════════════════════════════════════
#  ESTADO GLOBAL
# ══════════════════════════════════════════════════════════════════════════════
env_vars:     dict[int, dict]  = {}   # variáveis por servidor
cmd_history:  dict[int, list]  = {}   # histórico por canal
active_procs: dict[int, dict]  = {}   # processos ativos por usuário
boot_time     = time.time()

# ══════════════════════════════════════════════════════════════════════════════
#  SETUP DO BOT
# ══════════════════════════════════════════════════════════════════════════════
intents = discord.Intents.default()
intents.message_content = True
intents.guilds           = True
intents.members          = True

bot = commands.Bot(
    command_prefix="!!fox_interno__",
    intents=intents,
    help_command=None,
    case_insensitive=True
)

# ══════════════════════════════════════════════════════════════════════════════
#  VERIFICAÇÃO DE CARGO
# ══════════════════════════════════════════════════════════════════════════════
def tem_cargo(member: discord.Member) -> bool:
    """Verifica se o membro tem o cargo autorizado."""
    return any(r.id == CARGO_AUTORIZADO_ID for r in member.roles)

async def checar_cargo(message: discord.Message) -> bool:
    """Retorna True se pode usar. Manda embed de negação caso contrário."""
    if tem_cargo(message.author):
        return True

    embed = discord.Embed(
        title=f"{E_LOCK}  Acesso Negado",
        description=(
            f"{message.author.mention}, você **não tem permissão** para usar o Fox Terminal.\n\n"
            f"Apenas membros com o cargo <@&{CARGO_AUTORIZADO_ID}> podem usar este bot."
        ),
        color=COR_PROIBIDO,
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(
        name=f"{E_SHIELD} Cargo necessário",
        value=f"<@&{CARGO_AUTORIZADO_ID}>",
        inline=False
    )
    embed.set_footer(text=f"Fox Terminal {E_FOX}  •  Acesso restrito")
    await message.channel.send(embed=embed, delete_after=8)
    try:
        await message.delete()
    except Exception:
        pass
    return False

# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS UTILITÁRIOS
# ══════════════════════════════════════════════════════════════════════════════
def now_str() -> str:
    return datetime.now().strftime("%H:%M:%S")

def date_str() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

def uptime_str() -> str:
    secs = int(time.time() - boot_time)
    h, r = divmod(secs, 3600)
    m, s = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def truncate(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    if not text:
        return "(sem saída)"
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n... [{len(text) - limit} caracteres omitidos]"

def fmt_size(num_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} PB"

def record_history(channel_id: int, cmd: str, author: str):
    if channel_id not in cmd_history:
        cmd_history[channel_id] = []
    cmd_history[channel_id].append({
        "cmd": cmd, "time": now_str(),
        "date": date_str(), "author": author
    })
    cmd_history[channel_id] = cmd_history[channel_id][-100:]

def run_cmd_fast(cmd: str, timeout: int = CMD_TIMEOUT) -> tuple[str, str, int]:
    """Executa comando rápido com timeout."""
    try:
        r = subprocess.run(
            cmd, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=timeout,
            env={**os.environ, "DEBIAN_FRONTEND": "noninteractive",
                 "PIP_NO_INPUT": "1", "PYTHONDONTWRITEBYTECODE": "1"}
        )
        return r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired:
        return "", f"⏱ Tempo limite de {timeout}s excedido.", 1
    except Exception as e:
        return "", str(e), 1

def run_pip_fast(args: str, timeout: int = INSTALL_TIMEOUT) -> tuple[str, str, int]:
    """Executa pip com flags de velocidade máxima."""
    cmd = (
        f"{sys.executable} -m pip {args} "
        f"--no-cache-dir --quiet --quiet "        # sem cache = mais rápido no Colab
        f"--disable-pip-version-check "
        f"--no-warn-script-location "
        f"--prefer-binary"                        # usa wheels prontas (muito mais rápido)
    )
    return run_cmd_fast(cmd, timeout)

async def get_or_create_cat(guild: discord.Guild, nome: str = CATEGORIA_NOME) -> discord.CategoryChannel:
    cat = discord.utils.get(guild.categories, name=nome)
    if not cat:
        cat = await guild.create_category(nome, reason=f"Fox Terminal — categoria {nome}")
    return cat

async def log_action(guild: discord.Guild, author: discord.Member, cmd: str, status: str):
    """Loga ações no canal fox-logs."""
    try:
        cat  = await get_or_create_cat(guild)
        canal = discord.utils.get(guild.text_channels, name=LOG_CANAL_NOME)
        if not canal:
            canal = await guild.create_text_channel(
                LOG_CANAL_NOME, category=cat,
                topic=f"{E_LOG} Logs do Fox Terminal"
            )
        color = COR_OK if "ok" in status.lower() else COR_ERRO
        embed = discord.Embed(
            title=f"{E_LOG} Log de Ação",
            color=color,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Usuário", value=f"`{author.display_name}`", inline=True)
        embed.add_field(name="Comando", value=f"`{cmd[:100]}`",            inline=True)
        embed.add_field(name="Status",  value=f"`{status}`",               inline=True)
        embed.set_footer(text=f"Fox Terminal {E_FOX}")
        await canal.send(embed=embed)
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════════════════
#  SISTEMA DE LOADING ANIMADO
# ══════════════════════════════════════════════════════════════════════════════
FRAMES_SPIN   = ["◐", "◓", "◑", "◒"]
FRAMES_BLOCK  = ["░░░░░░░░░░", "█░░░░░░░░░", "██░░░░░░░░",
                 "███░░░░░░░", "████░░░░░░", "█████░░░░░",
                 "██████░░░░", "███████░░░", "████████░░",
                 "█████████░", "██████████"]
FRAMES_DOTS   = ["   ", ".  ", ".. ", "..."]
FRAMES_ARROWS = ["▹▹▹▹▹", "▸▹▹▹▹", "▹▸▹▹▹", "▹▹▸▹▹", "▹▹▹▸▹", "▹▹▹▹▸"]

class AnimatedLoader:
    """Gerencia uma mensagem de loading animada enquanto o comando executa."""

    def __init__(self, channel: discord.TextChannel, titulo: str,
                 cmd_str: str = "", pkg: str = ""):
        self.channel   = channel
        self.titulo    = titulo
        self.cmd_str   = cmd_str
        self.pkg       = pkg
        self.msg       = None
        self._stop     = False
        self._frame    = 0
        self._start    = time.time()
        self._task     = None

    def _elapsed(self) -> str:
        return f"{time.time() - self._start:.1f}s"

    def _make_embed(self, frame_idx: int) -> discord.Embed:
        spin    = FRAMES_SPIN[frame_idx % len(FRAMES_SPIN)]
        block   = FRAMES_BLOCK[min(frame_idx, len(FRAMES_BLOCK) - 1)]
        dots    = FRAMES_DOTS[frame_idx % len(FRAMES_DOTS)]
        arrows  = FRAMES_ARROWS[frame_idx % len(FRAMES_ARROWS)]

        # Linha de progresso animada
        prog = (
            f"```\n"
            f"{spin} {self.titulo}{dots}\n"
            f"[{block}] {min(frame_idx * 10, 95)}%\n"
            f"{arrows}  {self._elapsed()}\n"
            f"```"
        )

        embed = discord.Embed(
            title=f"{E_LOAD}  {self.titulo}",
            description=prog,
            color=COR_LOADING,
            timestamp=datetime.now(timezone.utc)
        )

        if self.cmd_str:
            embed.add_field(
                name=f"{E_TERM} Comando",
                value=f"```bash\n{self.cmd_str[:200]}\n```",
                inline=False
            )
        if self.pkg:
            embed.add_field(
                name=f"{E_PKG} Pacote",
                value=f"`{self.pkg}`",
                inline=True
            )
        embed.add_field(
            name=f"{E_CLOCK} Tempo",
            value=f"`{self._elapsed()}`",
            inline=True
        )
        embed.set_footer(text=f"Fox Terminal {E_FOX}  •  Processando...")
        return embed

    async def start(self) -> "AnimatedLoader":
        self.msg = await self.channel.send(embed=self._make_embed(0))
        self._task = asyncio.create_task(self._animate())
        return self

    async def _animate(self):
        await asyncio.sleep(0.8)
        frame = 1
        while not self._stop:
            try:
                await self.msg.edit(embed=self._make_embed(frame))
            except Exception:
                break
            frame += 1
            await asyncio.sleep(1.2)

    async def stop_ok(self, titulo: str, output: str, fields: list = None,
                      extra_info: dict = None):
        self._stop = True
        if self._task:
            self._task.cancel()
        await asyncio.sleep(0.1)

        elapsed = self._elapsed()
        desc    = f"```ansi\n{truncate(output, 2000)}\n```" if output.strip() else ""

        embed = discord.Embed(
            title=f"{E_OK}  {titulo}",
            description=desc,
            color=COR_OK,
            timestamp=datetime.now(timezone.utc)
        )
        if self.pkg:
            embed.add_field(name=f"{E_PKG} Pacote",    value=f"`{self.pkg}`",  inline=True)
        embed.add_field(name=f"{E_CLOCK} Tempo",        value=f"`{elapsed}`",   inline=True)
        embed.add_field(name=f"{E_FIRE} Status",         value="`Sucesso`",     inline=True)

        if extra_info:
            for k, v in extra_info.items():
                embed.add_field(name=k, value=v, inline=True)

        if fields:
            for name, value in fields:
                embed.add_field(name=name, value=str(value)[:1024], inline=False)

        if self.cmd_str:
            embed.add_field(
                name=f"{E_TERM} Comando executado",
                value=f"```bash\n{self.cmd_str[:200]}\n```",
                inline=False
            )

        embed.set_footer(text=f"Fox Terminal {E_FOX}  •  {now_str()}")
        try:
            await self.msg.edit(embed=embed)
        except Exception:
            await self.channel.send(embed=embed)

    async def stop_err(self, titulo: str, output: str):
        self._stop = True
        if self._task:
            self._task.cancel()
        await asyncio.sleep(0.1)

        elapsed = self._elapsed()
        embed = discord.Embed(
            title=f"{E_ERR}  {titulo}",
            description=f"```\n{truncate(output, 2500)}\n```" if output.strip() else "",
            color=COR_ERRO,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name=f"{E_CLOCK} Tempo",  value=f"`{elapsed}`",   inline=True)
        embed.add_field(name=f"{E_WARN} Status",  value="`Falhou`",       inline=True)
        if self.cmd_str:
            embed.add_field(
                name=f"{E_TERM} Comando",
                value=f"```bash\n{self.cmd_str[:200]}\n```",
                inline=False
            )
        embed.set_footer(text=f"Fox Terminal {E_FOX}  •  Erro em {now_str()}")
        try:
            await self.msg.edit(embed=embed)
        except Exception:
            await self.channel.send(embed=embed)


# ══════════════════════════════════════════════════════════════════════════════
#  DETECÇÃO DE COMANDOS (SEM PREFIXO)
# ══════════════════════════════════════════════════════════════════════════════
TERMINAL_CMDS = {
    # Python
    "pip", "pip3", "python", "python3", "conda", "pipenv", "poetry",
    # Node
    "npm", "npx", "yarn", "pnpm", "bun", "node",
    # Sistema
    "apt", "apt-get", "apt-cache", "dpkg", "snap", "flatpak",
    # Termux
    "pkg",
    # Rust
    "cargo", "rustup",
    # Ruby
    "gem", "bundle", "rails",
    # Go
    "go",
    # Java
    "mvn", "gradle", "javac",
    # PHP
    "composer", "php",
    # Git
    "git",
    # Shell / arquivo
    "mkdir", "ls", "ll", "la", "pwd", "cd", "rm", "cat",
    "echo", "touch", "mv", "cp", "chmod", "chown", "ln",
    "head", "tail", "grep", "wc", "sort", "uniq", "awk", "sed",
    "find", "locate", "which", "whereis",
    # Shell / processo
    "clear", "cls", "history", "env", "export", "unset",
    "ps", "kill", "killall", "top", "htop", "jobs",
    "whoami", "id", "groups",
    # Sistema
    "uname", "uptime", "date", "cal", "df", "du", "free",
    "lscpu", "lsblk", "lsusb", "lspci",
    # Rede
    "curl", "wget", "ping", "netstat", "ss", "ifconfig",
    "ip", "nmap", "traceroute", "nslookup", "dig", "host",
    # Docker
    "docker", "docker-compose",
    # Banco de dados
    "mysql", "psql", "sqlite3", "mongo", "redis-cli",
    # Editores (simulados)
    "nano", "vim", "vi", "code",
    # Fox Terminal
    "help", "--help", "-h", "fox", "fox-help",
    "man", "info",
}

def is_terminal_cmd(content: str) -> bool:
    first = content.strip().split()[0].lower() if content.strip() else ""
    # Remove versões como python3.11 -> python3
    first = re.split(r"[0-9]", first)[0]
    return first in TERMINAL_CMDS

def parse_cmd(content: str) -> tuple[str, list[str], str]:
    """Retorna (cmd, args, full_str)."""
    parts = content.strip().split()
    if not parts:
        return "", [], ""
    return parts[0].lower(), parts[1:], content.strip()


# ══════════════════════════════════════════════════════════════════════════════
#  BANCO DE DADOS DE PACOTES POPULARES (para sugestões)
# ══════════════════════════════════════════════════════════════════════════════
PKG_POPULARES_PIP = [
    "requests", "numpy", "pandas", "matplotlib", "seaborn", "scipy",
    "scikit-learn", "tensorflow", "torch", "keras", "opencv-python",
    "Pillow", "flask", "fastapi", "django", "sqlalchemy", "aiohttp",
    "httpx", "pydantic", "celery", "redis", "pymongo", "psycopg2",
    "boto3", "paramiko", "cryptography", "jwt", "bcrypt",
    "discord.py", "tweepy", "instagrapi", "selenium", "playwright",
    "beautifulsoup4", "scrapy", "lxml", "html5lib", "pyaudio",
    "tqdm", "rich", "click", "typer", "loguru", "python-dotenv",
    "pytest", "black", "flake8", "mypy", "isort", "autopep8",
]

PKG_POPULARES_NPM = [
    "express", "react", "vue", "angular", "next", "nuxt", "svelte",
    "typescript", "webpack", "vite", "rollup", "esbuild", "babel",
    "axios", "lodash", "moment", "dayjs", "uuid", "nanoid",
    "mongoose", "sequelize", "prisma", "typeorm",
    "discord.js", "telegraf", "socket.io", "ws",
    "jest", "vitest", "mocha", "chai", "eslint", "prettier",
    "dotenv", "nodemon", "pm2", "cors", "helmet", "jsonwebtoken",
]

PKG_TERMUX_MAP = {
    "python":      "python3",      "python3":     "python3",
    "nodejs":      "nodejs",       "nodejs-lts":  "nodejs",
    "git":         "git",          "vim":         "vim",
    "nano":        "nano",         "curl":        "curl",
    "wget":        "wget",         "cmake":       "cmake",
    "clang":       "clang",        "openssh":     "openssh-client",
    "ffmpeg":      "ffmpeg",       "lua54":       "lua5.4",
    "lua53":       "lua5.3",       "ruby":        "ruby",
    "golang":      "golang",       "rust":        "rustc",
    "sqlite":      "sqlite3",      "mysql":       "mysql-client",
    "postgresql":  "postgresql",   "redis":       "redis",
    "nginx":       "nginx",        "apache2":     "apache2",
    "php":         "php",          "java":        "default-jdk",
    "kotlin":      "kotlin",       "gradle":      "gradle",
    "maven":       "maven",        "docker":      "docker.io",
    "zip":         "zip",          "unzip":       "unzip",
    "tar":         "tar",          "gzip":        "gzip",
    "htop":        "htop",         "tree":        "tree",
    "jq":          "jq",           "bat":         "bat",
    "fd":          "fd-find",      "ripgrep":     "ripgrep",
    "fzf":         "fzf",          "tmux":        "tmux",
    "screen":      "screen",       "neovim":      "neovim",
    "zsh":         "zsh",          "fish":        "fish",
    "ffprobe":     "ffmpeg",       "imagemagick": "imagemagick",
    "pandoc":      "pandoc",       "latex":       "texlive",
    "R":           "r-base",       "perl":        "perl",
    "tcl":         "tcl",          "erlang":      "erlang",
    "elixir":      "elixir",       "scala":       "scala",
    "swift":       "swift",        "haskell":     "haskell-platform",
    "lisp":        "clisp",        "prolog":      "swi-prolog",
    "octave":      "octave",       "julia":       "julia",
    "mono":        "mono-devel",   "dotnet":      "dotnet-sdk-8",
    "openjdk-11":  "openjdk-11-jdk",
    "openjdk-17":  "openjdk-17-jdk",
    "openjdk-21":  "openjdk-21-jdk",
}


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLERS — PIP (Python)
# ══════════════════════════════════════════════════════════════════════════════
async def handle_pip(message: discord.Message, sub: list[str]):
    ch = message.channel
    if not sub:
        embed = discord.Embed(
            title=f"{E_PYTHON} pip — Gerenciador Python",
            color=COR_ROXO
        )
        cmds = (
            "`pip install <pkg>` — Instalar pacote\n"
            "`pip install <pkg>==<ver>` — Versão específica\n"
            "`pip install -r requirements.txt` — Do arquivo\n"
            "`pip uninstall <pkg>` — Desinstalar\n"
            "`pip list` — Listar instalados\n"
            "`pip show <pkg>` — Info do pacote\n"
            "`pip freeze` — Lista para requirements\n"
            "`pip search <pkg>` — Buscar pacotes\n"
            "`pip upgrade <pkg>` — Atualizar pacote\n"
            "`pip check` — Verificar dependências\n"
        )
        embed.add_field(name="Comandos", value=cmds, inline=False)
        embed.add_field(
            name=f"{E_STAR} Pacotes populares",
            value="`" + "` `".join(random.sample(PKG_POPULARES_PIP, 8)) + "`",
            inline=False
        )
        embed.set_footer(text=f"Fox Terminal {E_FOX}")
        await ch.send(embed=embed)
        return

    action = sub[0].lower()
    args   = sub[1:]

    # ── pip install ────────────────────────────────────────────────────────────
    if action == "install" and args:
        pkg_str = " ".join(args)
        loader  = await AnimatedLoader(
            ch, f"Instalando {pkg_str}",
            cmd_str=f"pip install {pkg_str} --prefer-binary",
            pkg=pkg_str
        ).start()

        # Executa em thread para não bloquear o event loop
        loop = asyncio.get_event_loop()
        out, err, code = await loop.run_in_executor(
            None, lambda: run_pip_fast(f"install {pkg_str}")
        )

        if code == 0:
            # Pega versão instalada
            pkg_base = args[0].split("==")[0].split(">=")[0]
            v_out, _, _ = run_cmd_fast(
                f"{sys.executable} -m pip show {pkg_base} 2>/dev/null"
            )
            version  = "?"
            home_url = ""
            summary  = ""
            for line in v_out.splitlines():
                if line.startswith("Version:"):
                    version = line.split(":", 1)[1].strip()
                elif line.startswith("Home-page:"):
                    home_url = line.split(":", 1)[1].strip()
                elif line.startswith("Summary:"):
                    summary = line.split(":", 1)[1].strip()

            await loader.stop_ok(
                f"Instalado: {pkg_base}",
                out or "Instalado com sucesso!",
                extra_info={
                    f"{E_PYTHON} Versão": f"`{version}`",
                    f"{E_GLOBE} URL":     f"`{home_url[:60]}`" if home_url else "`—`",
                    f"{E_INFO} Descrição": summary[:80] if summary else "—",
                }
            )
            await log_action(message.guild, message.author,
                             f"pip install {pkg_str}", f"OK v{version}")
        else:
            err_clean = err or out
            await loader.stop_err(f"Erro ao instalar {pkg_str}", err_clean)
            await log_action(message.guild, message.author,
                             f"pip install {pkg_str}", "ERRO")

    # ── pip uninstall ──────────────────────────────────────────────────────────
    elif action == "uninstall" and args:
        pkg = " ".join(args)
        loader = await AnimatedLoader(
            ch, f"Removendo {pkg}",
            cmd_str=f"pip uninstall {pkg} -y"
        ).start()
        loop = asyncio.get_event_loop()
        out, err, code = await loop.run_in_executor(
            None, lambda: run_cmd_fast(
                f"{sys.executable} -m pip uninstall {pkg} -y "
                f"--disable-pip-version-check", INSTALL_TIMEOUT
            )
        )
        if code == 0:
            await loader.stop_ok(f"Removido: {pkg}", out or "Removido com sucesso!")
        else:
            await loader.stop_err(f"Erro ao remover {pkg}", err or out)

    # ── pip list ───────────────────────────────────────────────────────────────
    elif action == "list":
        loader = await AnimatedLoader(ch, "Listando pacotes Python...").start()
        out, _, _ = run_cmd_fast(f"{sys.executable} -m pip list --format=columns")
        linhas = out.strip().splitlines()
        total  = max(0, len(linhas) - 2)  # Remove header
        await loader.stop_ok(
            f"Pacotes Python instalados ({total})",
            truncate(out),
            extra_info={f"{E_GRAPH} Total": f"`{total} pacotes`"}
        )

    # ── pip show ───────────────────────────────────────────────────────────────
    elif action == "show" and args:
        pkg = args[0]
        loader = await AnimatedLoader(ch, f"Buscando info: {pkg}...").start()
        out, err, code = run_cmd_fast(
            f"{sys.executable} -m pip show {pkg}"
        )
        if code == 0:
            await loader.stop_ok(f"{E_PKG} {pkg}", out)
        else:
            await loader.stop_err(f"Pacote não encontrado: {pkg}",
                                  f"Tente: `pip install {pkg}`")

    # ── pip freeze ─────────────────────────────────────────────────────────────
    elif action == "freeze":
        loader = await AnimatedLoader(ch, "pip freeze...").start()
        out, _, _ = run_cmd_fast(f"{sys.executable} -m pip freeze")
        await loader.stop_ok("pip freeze", truncate(out))

    # ── pip search ─────────────────────────────────────────────────────────────
    elif action == "search" and args:
        pkg = args[0]
        matches = [p for p in PKG_POPULARES_PIP if pkg.lower() in p.lower()]
        desc = (
            "```\n" + "\n".join(matches[:20]) + "\n```"
            if matches else
            f"Nenhum pacote popular encontrado para `{pkg}`.\n"
            f"Tente `pip install {pkg}` diretamente."
        )
        embed = discord.Embed(
            title=f"{E_PYTHON} pip search: {pkg}",
            description=desc, color=COR_ROXO
        )
        embed.set_footer(text=f"Fox Terminal {E_FOX}")
        await ch.send(embed=embed)

    # ── pip upgrade ────────────────────────────────────────────────────────────
    elif action in ("upgrade", "update") and args:
        pkg = args[0]
        loader = await AnimatedLoader(
            ch, f"Atualizando {pkg}...",
            cmd_str=f"pip install --upgrade {pkg} --prefer-binary"
        ).start()
        loop = asyncio.get_event_loop()
        out, err, code = await loop.run_in_executor(
            None, lambda: run_pip_fast(f"install --upgrade {pkg}")
        )
        if code == 0:
            await loader.stop_ok(f"Atualizado: {pkg}", out or "OK!")
        else:
            await loader.stop_err(f"Erro ao atualizar {pkg}", err or out)

    # ── pip check ─────────────────────────────────────────────────────────────
    elif action == "check":
        loader = await AnimatedLoader(ch, "Verificando dependências...").start()
        out, err, code = run_cmd_fast(f"{sys.executable} -m pip check")
        if code == 0:
            await loader.stop_ok("Dependências OK!", out or "Nenhum conflito encontrado.")
        else:
            await loader.stop_err("Conflitos encontrados", err or out)

    # ── pip genérico ───────────────────────────────────────────────────────────
    else:
        cmd_str = "pip " + " ".join(sub)
        loader  = await AnimatedLoader(ch, f"pip {action}...", cmd_str=cmd_str).start()
        loop    = asyncio.get_event_loop()
        out, err, code = await loop.run_in_executor(
            None, lambda: run_cmd_fast(
                f"{sys.executable} -m pip {' '.join(sub)}", INSTALL_TIMEOUT
            )
        )
        if code == 0:
            await loader.stop_ok(f"pip {action}", truncate(out or "OK"))
        else:
            await loader.stop_err(f"Erro: pip {action}", truncate(err or out))


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLERS — NPM / YARN / PNPM / BUN (Node.js)
# ══════════════════════════════════════════════════════════════════════════════
async def handle_node_pm(message: discord.Message, cmd: str, sub: list[str]):
    ch = message.channel
    if not sub:
        embed = discord.Embed(
            title=f"{E_NODE} {cmd} — Gerenciador Node.js",
            color=0x68A063
        )
        embed.add_field(
            name="Comandos",
            value=(
                f"`{cmd} install <pkg>` — Instalar\n"
                f"`{cmd} uninstall <pkg>` — Remover\n"
                f"`{cmd} list` — Listar pacotes\n"
                f"`{cmd} update <pkg>` — Atualizar\n"
                f"`{cmd} run <script>` — Executar script\n"
                f"`{cmd} init` — Criar package.json\n"
                f"`{cmd} outdated` — Pacotes desatualizados\n"
            ),
            inline=False
        )
        embed.add_field(
            name=f"{E_STAR} Pacotes populares",
            value="`" + "` `".join(random.sample(PKG_POPULARES_NPM, 8)) + "`",
            inline=False
        )
        embed.set_footer(text=f"Fox Terminal {E_FOX}")
        await ch.send(embed=embed)
        return

    cmd_str = f"{cmd} {' '.join(sub)}"
    loader  = await AnimatedLoader(
        ch, f"{cmd} {sub[0]}...",
        cmd_str=cmd_str,
        pkg=sub[1] if len(sub) > 1 else ""
    ).start()

    loop = asyncio.get_event_loop()
    out, err, code = await loop.run_in_executor(
        None, lambda: run_cmd_fast(cmd_str, INSTALL_TIMEOUT)
    )
    action = sub[0].lower()
    if code == 0:
        await loader.stop_ok(f"{cmd} {action}", truncate(out or "OK"))
        if action in ("install", "i", "add"):
            await log_action(message.guild, message.author, cmd_str, "OK")
    else:
        err_msg = err or out
        if "not found" in err_msg.lower() or "command not found" in err_msg.lower():
            err_msg = (
                f"{cmd} não encontrado no sistema.\n"
                f"Instale com: `apt install nodejs npm -y`\n\n"
                f"Erro original:\n{err_msg}"
            )
        await loader.stop_err(f"Erro: {cmd} {action}", truncate(err_msg))


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLERS — APT (Sistema)
# ══════════════════════════════════════════════════════════════════════════════
async def handle_apt(message: discord.Message, sub: list[str], base: str = "apt-get"):
    ch = message.channel
    if not sub:
        embed = discord.Embed(
            title=f"{E_SYS} apt — Gerenciador do Sistema",
            color=COR_INFO
        )
        embed.add_field(
            name="Comandos",
            value=(
                "`apt install <pkg>` — Instalar\n"
                "`apt remove <pkg>` — Remover\n"
                "`apt update` — Atualizar lista\n"
                "`apt upgrade` — Atualizar tudo\n"
                "`apt search <pkg>` — Buscar\n"
                "`apt show <pkg>` — Info\n"
                "`apt list --installed` — Listados\n"
                "`apt autoremove` — Limpar órfãos\n"
            ),
            inline=False
        )
        embed.set_footer(text=f"Fox Terminal {E_FOX}")
        await ch.send(embed=embed)
        return

    action  = sub[0].lower()
    pkg_str = " ".join(sub[1:]) if len(sub) > 1 else ""
    env_apt = {"DEBIAN_FRONTEND": "noninteractive", "APT_LISTCHANGES_FRONTEND": "none"}

    if action in ("install", "remove", "purge", "reinstall"):
        if not pkg_str:
            await message.channel.send(
                embed=discord.Embed(
                    description=f"```\napt {action} <pacote>\n```",
                    color=COR_ERRO
                )
            )
            return
        loader = await AnimatedLoader(
            ch, f"apt {action} {pkg_str}",
            cmd_str=f"sudo {base} {action} {pkg_str} -y",
            pkg=pkg_str
        ).start()
        loop = asyncio.get_event_loop()
        out, err, code = await loop.run_in_executor(
            None, lambda: run_cmd_fast(
                f"sudo {base} {action} {pkg_str} -y 2>&1", 180
            )
        )
        if code == 0:
            await loader.stop_ok(f"apt {action}: {pkg_str}", truncate(out))
        else:
            await loader.stop_err(f"Erro: apt {action} {pkg_str}", truncate(err or out))

    elif action in ("update",):
        loader = await AnimatedLoader(ch, "apt update...", cmd_str="sudo apt-get update").start()
        loop = asyncio.get_event_loop()
        out, err, code = await loop.run_in_executor(
            None, lambda: run_cmd_fast("sudo apt-get update 2>&1", 120)
        )
        if code == 0:
            await loader.stop_ok("apt update concluído", truncate(out))
        else:
            await loader.stop_err("Erro: apt update", truncate(err or out))

    elif action in ("upgrade", "full-upgrade", "dist-upgrade"):
        loader = await AnimatedLoader(
            ch, f"apt {action}...",
            cmd_str=f"sudo {base} {action} -y"
        ).start()
        loop = asyncio.get_event_loop()
        out, err, code = await loop.run_in_executor(
            None, lambda: run_cmd_fast(f"sudo {base} {action} -y 2>&1", 300)
        )
        if code == 0:
            await loader.stop_ok(f"apt {action} concluído", truncate(out))
        else:
            await loader.stop_err(f"Erro: apt {action}", truncate(err or out))

    elif action == "search" and pkg_str:
        loader = await AnimatedLoader(ch, f"Buscando {pkg_str}...").start()
        out, _, _ = run_cmd_fast(f"apt-cache search {pkg_str} 2>&1 | head -30")
        await loader.stop_ok(f"apt search: {pkg_str}", truncate(out or "Nenhum resultado."))

    elif action in ("show", "info") and pkg_str:
        loader = await AnimatedLoader(ch, f"Info: {pkg_str}...").start()
        out, err, code = run_cmd_fast(f"apt-cache show {pkg_str} 2>&1 | head -40")
        if code == 0 or out.strip():
            await loader.stop_ok(f"apt show: {pkg_str}", truncate(out))
        else:
            await loader.stop_err(f"Não encontrado: {pkg_str}", err or out)

    elif action == "autoremove":
        loader = await AnimatedLoader(ch, "apt autoremove...",
                                      cmd_str="sudo apt-get autoremove -y").start()
        loop = asyncio.get_event_loop()
        out, err, code = await loop.run_in_executor(
            None, lambda: run_cmd_fast("sudo apt-get autoremove -y 2>&1", 120)
        )
        if code == 0:
            await loader.stop_ok("apt autoremove concluído", truncate(out))
        else:
            await loader.stop_err("Erro: apt autoremove", truncate(err or out))

    elif action == "list":
        loader = await AnimatedLoader(ch, "Listando pacotes...").start()
        flags  = " ".join(sub[1:])
        out, _, _ = run_cmd_fast(f"apt list {flags} 2>/dev/null | head -50")
        await loader.stop_ok("apt list", truncate(out))

    else:
        cmd_str = f"sudo {base} {' '.join(sub)} -y 2>&1"
        loader  = await AnimatedLoader(ch, f"apt {action}...", cmd_str=cmd_str).start()
        loop = asyncio.get_event_loop()
        out, err, code = await loop.run_in_executor(
            None, lambda: run_cmd_fast(cmd_str, 180)
        )
        if code == 0:
            await loader.stop_ok(f"apt {action}", truncate(out or "OK"))
        else:
            await loader.stop_err(f"Erro: apt {action}", truncate(err or out))


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLERS — PKG (Termux)
# ══════════════════════════════════════════════════════════════════════════════
async def handle_pkg(message: discord.Message, sub: list[str]):
    ch = message.channel
    if not sub:
        embed = discord.Embed(
            title=f"{E_PKG} pkg — Gerenciador Termux",
            description="Instala pacotes no estilo Termux, mapeados para apt no Colab.",
            color=0x00BCD4
        )
        embed.add_field(
            name="Comandos",
            value=(
                "`pkg install <pkg>` — Instalar\n"
                "`pkg uninstall <pkg>` — Remover\n"
                "`pkg update` — Atualizar lista\n"
                "`pkg upgrade` — Atualizar tudo\n"
                "`pkg search <pkg>` — Buscar\n"
                "`pkg list-installed` — Instalados\n"
                "`pkg list-all` — Todos disponíveis\n"
                "`pkg show <pkg>` — Informações\n"
            ),
            inline=False
        )
        embed.add_field(
            name=f"{E_STAR} Pacotes Termux disponíveis",
            value="`" + "` `".join(list(PKG_TERMUX_MAP.keys())[:20]) + "`",
            inline=False
        )
        embed.set_footer(text=f"Fox Terminal {E_FOX}  •  Termux-style")
        await ch.send(embed=embed)
        return

    action = sub[0].lower()

    if action == "install" and len(sub) > 1:
        pkg_orig = sub[1]
        pkg_apt  = PKG_TERMUX_MAP.get(pkg_orig, pkg_orig)
        loader   = await AnimatedLoader(
            ch, f"pkg install {pkg_orig}",
            cmd_str=f"sudo apt-get install {pkg_apt} -y",
            pkg=pkg_orig
        ).start()
        loop = asyncio.get_event_loop()
        out, err, code = await loop.run_in_executor(
            None, lambda: run_cmd_fast(
                f"sudo apt-get install {pkg_apt} -y 2>&1", 180
            )
        )
        if code == 0:
            await loader.stop_ok(
                f"Instalado: {pkg_orig}",
                truncate(out or "Instalado!"),
                extra_info={
                    f"{E_PKG} Termux": f"`{pkg_orig}`",
                    f"{E_SYS} apt":    f"`{pkg_apt}`",
                }
            )
        else:
            await loader.stop_err(f"Erro: pkg install {pkg_orig}", truncate(err or out))

    elif action in ("update", "upgrade"):
        loader = await AnimatedLoader(ch, f"pkg {action}...",
                                      cmd_str=f"sudo apt-get {action} -y").start()
        loop = asyncio.get_event_loop()
        out, err, code = await loop.run_in_executor(
            None, lambda: run_cmd_fast(f"sudo apt-get {action} -y 2>&1", 300)
        )
        if code == 0:
            await loader.stop_ok(f"pkg {action} concluído", truncate(out))
        else:
            await loader.stop_err(f"Erro: pkg {action}", truncate(err or out))

    elif action == "uninstall" and len(sub) > 1:
        pkg = PKG_TERMUX_MAP.get(sub[1], sub[1])
        loader = await AnimatedLoader(ch, f"pkg uninstall {sub[1]}...",
                                      cmd_str=f"sudo apt-get remove {pkg} -y").start()
        loop = asyncio.get_event_loop()
        out, err, code = await loop.run_in_executor(
            None, lambda: run_cmd_fast(f"sudo apt-get remove {pkg} -y 2>&1", 60)
        )
        if code == 0:
            await loader.stop_ok(f"Removido: {sub[1]}", truncate(out))
        else:
            await loader.stop_err(f"Erro: pkg uninstall {sub[1]}", truncate(err or out))

    elif action == "list-installed":
        loader = await AnimatedLoader(ch, "Listando instalados...").start()
        out, _, _ = run_cmd_fast("dpkg -l 2>/dev/null | awk 'NR>5{print $2,$3}' | head -50")
        await loader.stop_ok("Pacotes instalados", truncate(out))

    elif action == "list-all":
        loader = await AnimatedLoader(ch, "Listando todos os pacotes...").start()
        pkgs   = "\n".join(
            f"  {orig:<20} -> {apt}" for orig, apt in list(PKG_TERMUX_MAP.items())[:50]
        )
        await loader.stop_ok(
            f"Pacotes disponíveis ({len(PKG_TERMUX_MAP)})",
            f"{'Termux':<20} {'apt-get'}\n{'─'*40}\n{pkgs}"
        )

    elif action == "search" and len(sub) > 1:
        q = sub[1].lower()
        matches = {k: v for k, v in PKG_TERMUX_MAP.items() if q in k.lower() or q in v.lower()}
        if matches:
            result = "\n".join(f"  {k:<20} -> {v}" for k, v in matches.items())
            await message.channel.send(
                embed=discord.Embed(
                    title=f"{E_PKG} pkg search: {q}",
                    description=f"```\n{'Termux':<20} apt-get\n{'─'*40}\n{result}\n```",
                    color=0x00BCD4
                )
            )
        else:
            await message.channel.send(
                embed=discord.Embed(
                    description=f"Nenhum pacote encontrado para `{q}`.",
                    color=COR_AVISO
                )
            )

    elif action == "show" and len(sub) > 1:
        pkg_apt = PKG_TERMUX_MAP.get(sub[1], sub[1])
        loader  = await AnimatedLoader(ch, f"pkg show {sub[1]}...").start()
        out, _, _ = run_cmd_fast(f"apt-cache show {pkg_apt} 2>&1 | head -30")
        await loader.stop_ok(f"pkg show: {sub[1]}", truncate(out or "Não encontrado."))

    else:
        cmd_str = "apt-get " + " ".join(sub) + " -y 2>&1"
        loader  = await AnimatedLoader(ch, f"pkg {action}...", cmd_str=cmd_str).start()
        loop = asyncio.get_event_loop()
        out, err, code = await loop.run_in_executor(
            None, lambda: run_cmd_fast(cmd_str, 180)
        )
        if code == 0:
            await loader.stop_ok(f"pkg {action}", truncate(out or "OK"))
        else:
            await loader.stop_err(f"Erro: pkg {action}", truncate(err or out))


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLERS — CARGO / GEM / GO / COMPOSER / MAVEN / GRADLE
# ══════════════════════════════════════════════════════════════════════════════
async def handle_generic_pm(message: discord.Message, cmd: str, sub: list[str],
                             emoji: str = E_PKG, timeout: int = INSTALL_TIMEOUT):
    ch      = message.channel
    cmd_str = f"{cmd} {' '.join(sub)}"
    action  = sub[0].lower() if sub else cmd
    pkg     = sub[1] if len(sub) > 1 else ""

    loader = await AnimatedLoader(
        ch, f"{emoji} {cmd} {action}...",
        cmd_str=cmd_str, pkg=pkg
    ).start()

    loop = asyncio.get_event_loop()
    out, err, code = await loop.run_in_executor(
        None, lambda: run_cmd_fast(cmd_str, timeout)
    )

    if code == 0:
        await loader.stop_ok(f"{cmd} {action}", truncate(out or "OK"))
        await log_action(message.guild, message.author, cmd_str, "OK")
    else:
        err_msg = err or out
        if "not found" in err_msg.lower() or "No such file" in err_msg:
            err_msg = (
                f"`{cmd}` não encontrado.\n"
                f"Instale primeiro com `apt install` ou `pkg install`.\n\n"
                f"Erro:\n{err_msg}"
            )
        await loader.stop_err(f"Erro: {cmd} {action}", truncate(err_msg))


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLERS — GIT
# ══════════════════════════════════════════════════════════════════════════════
async def handle_git(message: discord.Message, sub: list[str]):
    ch = message.channel
    if not sub:
        embed = discord.Embed(
            title=f"{E_GIT} git — Controle de Versão",
            color=0xF05032
        )
        embed.add_field(
            name="Repositório",
            value=(
                "`git clone <url>` — Clonar repo\n"
                "`git init` — Inicializar repo\n"
                "`git status` — Status\n"
                "`git log --oneline -10` — Últimos commits\n"
            ),
            inline=True
        )
        embed.add_field(
            name="Mudanças",
            value=(
                "`git add .` — Adicionar tudo\n"
                "`git add <file>` — Arquivo específico\n"
                "`git commit -m 'msg'` — Commitar\n"
                "`git diff` — Ver diferenças\n"
            ),
            inline=True
        )
        embed.add_field(
            name="Remoto",
            value=(
                "`git push` — Enviar\n"
                "`git pull` — Baixar\n"
                "`git fetch` — Buscar\n"
                "`git remote -v` — Remotos\n"
            ),
            inline=True
        )
        embed.add_field(
            name="Branches",
            value=(
                "`git branch` — Listar\n"
                "`git branch <nome>` — Criar\n"
                "`git checkout <branch>` — Mudar\n"
                "`git merge <branch>` — Mesclar\n"
                "`git rebase <branch>` — Rebase\n"
                "`git stash` — Guardar\n"
                "`git tag <nome>` — Criar tag\n"
            ),
            inline=True
        )
        embed.set_footer(text=f"Fox Terminal {E_FOX}  •  Git")
        await ch.send(embed=embed)
        return

    action  = sub[0].lower()
    cmd_str = "git " + " ".join(sub)
    timeout = 60 if action not in ("clone", "push", "pull", "fetch") else 120

    loader = await AnimatedLoader(
        ch, f"git {action}...", cmd_str=cmd_str,
        pkg=sub[1] if len(sub) > 1 else ""
    ).start()

    loop = asyncio.get_event_loop()
    out, err, code = await loop.run_in_executor(
        None, lambda: run_cmd_fast(cmd_str, timeout)
    )

    output = out or err or "(sem saída)"
    if code == 0:
        await loader.stop_ok(f"git {action}", truncate(output))
    else:
        await loader.stop_err(f"Erro: git {action}", truncate(err or out))


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLERS — MKDIR (Criar canal no Discord)
# ══════════════════════════════════════════════════════════════════════════════
async def handle_mkdir(message: discord.Message, sub: list[str]):
    ch    = message.channel
    guild = message.guild

    if not sub:
        embed = discord.Embed(
            title=f"{E_FOLDER} mkdir — Criar Canal",
            description=(
                "Cria um canal de texto na categoria **TERMINAL**.\n\n"
                "```bash\nmkdir <nome-do-canal>\nmkdir projeto-python\nmkdir meu-servidor\n```"
            ),
            color=COR_INFO
        )
        await ch.send(embed=embed)
        return

    nome_raw  = " ".join(sub)
    nome_slug = re.sub(r"[^a-z0-9\-]", "-", nome_raw.lower().strip()).strip("-")
    nome_slug = re.sub(r"-{2,}", "-", nome_slug)

    if not nome_slug or len(nome_slug) < 1:
        await ch.send(embed=discord.Embed(
            description=f"{E_ERR} Nome inválido. Use letras e números.",
            color=COR_ERRO
        ))
        return

    loader = await AnimatedLoader(
        ch, f"Criando canal #{nome_slug}...",
        cmd_str=f"mkdir {nome_slug}"
    ).start()

    try:
        cat = await get_or_create_cat(guild)

        # Verifica se já existe
        existente = discord.utils.get(cat.channels, name=nome_slug)
        if existente:
            await loader.stop_err(
                "Canal já existe",
                f"#{nome_slug} já existe em {CATEGORIA_NOME}.\nEscolha outro nome."
            )
            return

        novo = await guild.create_text_channel(
            name=nome_slug,
            category=cat,
            topic=(
                f"{E_FOLDER} Criado por {message.author.display_name} "
                f"via Fox Terminal • {date_str()}"
            ),
            reason=f"Fox Terminal mkdir por {message.author}"
        )

        embed_ok = discord.Embed(
            title=f"{E_OK}  Canal criado com sucesso!",
            color=COR_OK,
            timestamp=datetime.now(timezone.utc)
        )
        embed_ok.add_field(name=f"{E_FOLDER} Canal",    value=novo.mention,                    inline=True)
        embed_ok.add_field(name=f"{E_PKG} Categoria",   value=f"`{CATEGORIA_NOME}`",           inline=True)
        embed_ok.add_field(name="👤 Criado por",        value=message.author.mention,          inline=True)
        embed_ok.add_field(name=f"{E_CLOCK} Horário",   value=f"`{now_str()}`",                inline=True)
        embed_ok.add_field(name=f"{E_TERM} Comando",    value=f"```bash\nmkdir {nome_slug}\n```", inline=False)
        embed_ok.set_footer(text=f"Fox Terminal {E_FOX}  •  mkdir")

        loader._stop = True
        if loader._task:
            loader._task.cancel()
        await asyncio.sleep(0.1)
        await loader.msg.edit(embed=embed_ok)

        # Mensagem de boas-vindas no novo canal
        welcome = discord.Embed(
            title=f"{E_FOLDER}  {nome_slug}",
            description=(
                f"Canal criado por {message.author.mention}.\n\n"
                "```bash\n"
                f"$ pwd\n/{CATEGORIA_NOME}/{nome_slug}\n\n"
                f"$ ls -la\ntotal 0\n\n"
                f"$ echo 'Fox Terminal pronto!'\nFox Terminal pronto!\n"
                "```"
            ),
            color=COR_TERMINAL,
            timestamp=datetime.now(timezone.utc)
        )
        welcome.set_footer(text=f"Fox Terminal {E_FOX}  •  {date_str()}")
        await novo.send(embed=welcome)
        await log_action(guild, message.author, f"mkdir {nome_slug}", "OK")

    except discord.Forbidden:
        await loader.stop_err("Sem permissão", "O bot precisa de **Gerenciar Canais**.")
    except Exception as e:
        await loader.stop_err("Erro ao criar canal", str(e))


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLERS — LS (Listar canais)
# ══════════════════════════════════════════════════════════════════════════════
async def handle_ls(message: discord.Message, sub: list[str]):
    guild = message.guild
    cat   = discord.utils.get(guild.categories, name=CATEGORIA_NOME)

    if not cat or not cat.channels:
        embed = discord.Embed(
            title=f"{E_FOLDER} ls /{CATEGORIA_NOME}",
            description=(
                f"Categoria `{CATEGORIA_NOME}` vazia ou não existe.\n"
                f"Use `mkdir <nome>` para criar um canal."
            ),
            color=COR_INFO
        )
        await message.channel.send(embed=embed)
        return

    linhas = []
    for ch in sorted(cat.channels, key=lambda c: c.name):
        tipo  = "d" if isinstance(ch, discord.CategoryChannel) else "-"
        perms = "rwxr-xr-x"
        size  = len(ch.members) if hasattr(ch, "members") else 0
        data  = ch.created_at.strftime("%b %d %H:%M") if ch.created_at else "---"
        linhas.append(f"{tipo}{perms}  1 fox fox {size:>4}  {data}  {E_FOLDER} {ch.name}")

    total_str = f"total {len(cat.channels)}"
    desc      = f"```\n{total_str}\n" + "\n".join(linhas) + "\n```"

    embed = discord.Embed(
        title=f"{E_FOLDER}  /{CATEGORIA_NOME}",
        description=desc,
        color=COR_INFO,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text=f"{len(cat.channels)} canal(is)  •  Fox Terminal")
    await message.channel.send(embed=embed)


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLERS — RM (Deletar canal)
# ══════════════════════════════════════════════════════════════════════════════
async def handle_rm(message: discord.Message, sub: list[str]):
    ch    = message.channel
    guild = message.guild

    if not sub or sub[-1] in ("-rf", "-r", "-f"):
        await ch.send(embed=discord.Embed(
            description=f"```bash\nrm <nome-do-canal>\nrm -rf <nome>   # força remoção\n```",
            color=COR_ERRO
        ))
        return

    nome = sub[-1].lstrip("#")
    cat  = discord.utils.get(guild.categories, name=CATEGORIA_NOME)

    if not cat:
        await ch.send(embed=discord.Embed(
            description=f"{E_ERR} Categoria `{CATEGORIA_NOME}` não existe.",
            color=COR_ERRO
        ))
        return

    alvo = discord.utils.get(cat.channels, name=nome)
    if not alvo:
        await ch.send(embed=discord.Embed(
            description=(
                f"{E_ERR} Canal `{nome}` não encontrado em `{CATEGORIA_NOME}`.\n"
                f"Use `ls` para ver os canais disponíveis."
            ),
            color=COR_ERRO
        ))
        return

    loader = await AnimatedLoader(ch, f"rm {nome}...", cmd_str=f"rm -rf {nome}").start()
    try:
        await alvo.delete(reason=f"Fox Terminal rm por {message.author}")
        await loader.stop_ok(f"Removido: #{nome}", f"Canal `{nome}` deletado com sucesso.")
        await log_action(guild, message.author, f"rm {nome}", "OK")
    except discord.Forbidden:
        await loader.stop_err("Sem permissão", "Preciso de **Gerenciar Canais**.")
    except Exception as e:
        await loader.stop_err("Erro ao remover", str(e))


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLERS — SHELL BÁSICO
# ══════════════════════════════════════════════════════════════════════════════
async def handle_pwd(message: discord.Message):
    cat    = message.channel.category
    caminho = f"/{message.guild.name}/{cat.name if cat else 'root'}/{message.channel.name}"
    await message.channel.send(embed=discord.Embed(
        title="📍 pwd",
        description=f"```\n{caminho}\n```",
        color=COR_INFO
    ))

async def handle_echo(message: discord.Message, sub: list[str]):
    texto = " ".join(sub)
    # Substitui variáveis de ambiente do Fox
    ev = env_vars.get(message.guild.id, {})
    for k, v in ev.items():
        texto = texto.replace(f"${k}", v)
    await message.channel.send(embed=discord.Embed(
        description=f"```\n{texto}\n```", color=COR_INFO
    ))

async def handle_clear(message: discord.Message):
    try:
        await message.channel.purge(limit=50)
        m = await message.channel.send(embed=discord.Embed(
            title=f"{E_OK} clear",
            description="Últimas 50 mensagens apagadas.",
            color=COR_OK
        ))
        await asyncio.sleep(3)
        await m.delete()
    except discord.Forbidden:
        await message.channel.send(embed=discord.Embed(
            description=f"{E_ERR} Sem permissão para **Gerenciar Mensagens**.",
            color=COR_ERRO
        ))

async def handle_env(message: discord.Message):
    ev = env_vars.get(message.guild.id, {})
    if not ev:
        desc = "Nenhuma variável definida.\nUse `export VAR=valor`"
    else:
        desc = "```bash\n" + "\n".join(f"export {k}={v}" for k, v in ev.items()) + "\n```"
    await message.channel.send(embed=discord.Embed(
        title=f"🌿 Variáveis de Ambiente", description=desc, color=COR_INFO
    ))

async def handle_export(message: discord.Message, sub: list[str]):
    raw = " ".join(sub)
    if "=" not in raw:
        await message.channel.send(embed=discord.Embed(
            description="```bash\nexport VAR=valor\n```", color=COR_ERRO
        ))
        return
    k, _, v = raw.partition("=")
    gid = message.guild.id
    if gid not in env_vars:
        env_vars[gid] = {}
    env_vars[gid][k.strip()] = v.strip()
    await message.channel.send(embed=discord.Embed(
        title=f"{E_OK} export",
        description=f"```bash\nexport {k.strip()}={v.strip()}\n```",
        color=COR_OK
    ))

async def handle_history(message: discord.Message):
    hist = cmd_history.get(message.channel.id, [])
    if not hist:
        await message.channel.send(embed=discord.Embed(
            description="Nenhum comando no histórico ainda.", color=COR_INFO
        ))
        return
    linhas = "\n".join(
        f"{i+1:>4}  [{h['time']}]  {h['author']:<16}  {h['cmd']}"
        for i, h in enumerate(hist[-30:])
    )
    await message.channel.send(embed=discord.Embed(
        title=f"{E_LOG} Histórico ({len(hist)} comandos)",
        description=f"```\n{'#':>4}  Hora      Usuário           Comando\n{'─'*60}\n{truncate(linhas, 1800)}\n```",
        color=COR_INFO
    ))

async def handle_whoami(message: discord.Message):
    u     = message.author
    roles = [r.name for r in u.roles if r.name != "@everyone"]
    embed = discord.Embed(title=f"👤 whoami", color=COR_INFO,
                          timestamp=datetime.now(timezone.utc))
    embed.add_field(name="Usuário",  value=f"`{u.name}`",             inline=True)
    embed.add_field(name="ID",       value=f"`{u.id}`",               inline=True)
    embed.add_field(name="Apelido",  value=f"`{u.display_name}`",     inline=True)
    embed.add_field(name="Cargos",   value=", ".join(f"`{r}`" for r in roles[:5]) or "`—`", inline=False)
    embed.add_field(name="Conta criada", value=f"`{u.created_at.strftime('%d/%m/%Y')}`", inline=True)
    embed.set_thumbnail(url=u.display_avatar.url)
    embed.set_footer(text=f"Fox Terminal {E_FOX}")
    await message.channel.send(embed=embed)

async def handle_uname(message: discord.Message):
    out_u, _, _  = run_cmd_fast("uname -a")
    out_os, _, _ = run_cmd_fast("cat /etc/os-release 2>/dev/null | head -5")
    mem, _, _    = run_cmd_fast("free -h 2>/dev/null | head -2")
    embed = discord.Embed(title=f"{E_TERM} uname — Info do Sistema",
                          color=COR_INFO, timestamp=datetime.now(timezone.utc))
    embed.add_field(name="Kernel",    value=f"```{out_u.strip()[:100]}```", inline=False)
    embed.add_field(name="SO",        value=f"```{out_os.strip()[:200]}```", inline=False)
    embed.add_field(name="Memória",   value=f"```{mem.strip()[:200]}```",   inline=False)
    embed.add_field(name="Python",    value=f"`{sys.version.split()[0]}`",  inline=True)
    embed.add_field(name="discord.py",value=f"`{discord.__version__}`",    inline=True)
    embed.add_field(name="Bot uptime",value=f"`{uptime_str()}`",           inline=True)
    embed.set_footer(text=f"Fox Terminal {E_FOX}")
    await message.channel.send(embed=embed)

async def handle_ps(message: discord.Message):
    out, _, _ = run_cmd_fast("ps aux --sort=-%cpu 2>/dev/null | head -15")
    await message.channel.send(embed=discord.Embed(
        title=f"{E_GEAR} ps — Processos",
        description=f"```\n{truncate(out, 1800)}\n```", color=COR_INFO
    ))

async def handle_df(message: discord.Message):
    out, _, _ = run_cmd_fast("df -h 2>/dev/null")
    await message.channel.send(embed=discord.Embed(
        title=f"💾 df — Uso de Disco",
        description=f"```\n{truncate(out, 1800)}\n```", color=COR_INFO
    ))

async def handle_free(message: discord.Message):
    out, _, _ = run_cmd_fast("free -h 2>/dev/null")
    await message.channel.send(embed=discord.Embed(
        title=f"🧠 free — Memória RAM",
        description=f"```\n{truncate(out, 1000)}\n```", color=COR_INFO
    ))

async def handle_uptime(message: discord.Message):
    out, _, _ = run_cmd_fast("uptime 2>/dev/null")
    embed = discord.Embed(title=f"{E_CLOCK} uptime", color=COR_INFO)
    embed.add_field(name="Sistema",   value=f"```{out.strip()}```",   inline=False)
    embed.add_field(name="Bot",       value=f"`{uptime_str()}`",      inline=True)
    embed.add_field(name="Data/hora", value=f"`{date_str()}`",        inline=True)
    await message.channel.send(embed=embed)

async def handle_date(message: discord.Message):
    out, _, _ = run_cmd_fast("date")
    await message.channel.send(embed=discord.Embed(
        title=f"{E_CLOCK} date",
        description=f"```\n{out.strip()}\n```", color=COR_INFO
    ))

async def handle_grep(message: discord.Message, sub: list[str]):
    cmd_str = "grep " + " ".join(sub)
    out, err, code = run_cmd_fast(cmd_str, 10)
    if code == 0:
        await message.channel.send(embed=discord.Embed(
            title=f"🔍 grep", description=f"```\n{truncate(out)}\n```", color=COR_OK
        ))
    else:
        await message.channel.send(embed=discord.Embed(
            description=f"```\n{truncate(err or 'Sem resultado.')}\n```", color=COR_AVISO
        ))

async def handle_find(message: discord.Message, sub: list[str]):
    cmd_str = "find " + " ".join(sub) + " 2>/dev/null | head -30"
    out, err, code = run_cmd_fast(cmd_str, 15)
    await message.channel.send(embed=discord.Embed(
        title=f"🔍 find", description=f"```\n{truncate(out or err or 'Nenhum resultado.')}\n```",
        color=COR_INFO
    ))

async def handle_curl_wget(message: discord.Message, cmd: str, sub: list[str]):
    if not sub:
        await message.channel.send(embed=discord.Embed(
            description=f"```bash\n{cmd} <url>\n```", color=COR_ERRO
        ))
        return
    cmd_str = f"{cmd} " + " ".join(sub)
    loader  = await AnimatedLoader(
        message.channel, f"{E_GLOBE} {cmd}...", cmd_str=cmd_str
    ).start()
    loop = asyncio.get_event_loop()
    out, err, code = await loop.run_in_executor(
        None, lambda: run_cmd_fast(cmd_str + " 2>&1", 30)
    )
    if code == 0:
        await loader.stop_ok(f"{cmd} concluído", truncate(out or "OK"))
    else:
        await loader.stop_err(f"Erro: {cmd}", truncate(err or out))

async def handle_docker(message: discord.Message, sub: list[str]):
    ch      = message.channel
    cmd_str = "docker " + " ".join(sub)
    loader  = await AnimatedLoader(ch, f"{E_DOCKER} docker {sub[0] if sub else ''}...",
                                   cmd_str=cmd_str).start()
    loop = asyncio.get_event_loop()
    out, err, code = await loop.run_in_executor(
        None, lambda: run_cmd_fast(cmd_str, 120)
    )
    if code == 0:
        await loader.stop_ok(f"docker {sub[0] if sub else ''}", truncate(out or "OK"))
    else:
        await loader.stop_err(f"Erro: {cmd_str}", truncate(err or out))


# ══════════════════════════════════════════════════════════════════════════════
#  HELP MEGA COMPLETO
# ══════════════════════════════════════════════════════════════════════════════
async def handle_help(message: discord.Message, sub: list[str]):
    ch = message.channel

    if sub:
        # Help específico
        topic = sub[0].lower()
        helps = {
            "pip":    (f"{E_PYTHON} pip", "install / uninstall / list / show / freeze / search / upgrade / check"),
            "npm":    (f"{E_NODE} npm",   "install / uninstall / list / run / init / outdated / update"),
            "apt":    (f"{E_SYS} apt",    "install / remove / update / upgrade / search / show / autoremove / list"),
            "pkg":    (f"{E_PKG} pkg",    "install / uninstall / update / upgrade / search / list-installed / list-all / show"),
            "git":    (f"{E_GIT} git",    "clone / status / log / add / commit / push / pull / diff / branch / checkout / merge / stash / tag"),
            "mkdir":  (f"{E_FOLDER} mkdir", "Cria canal no Discord em TERMINAL"),
            "ls":     (f"{E_FOLDER} ls",    "Lista canais da categoria TERMINAL"),
            "docker": (f"{E_DOCKER} docker","build / run / ps / images / pull / stop / rm / rmi"),
        }
        if topic in helps:
            title, cmds = helps[topic]
            embed = discord.Embed(title=title, description=f"```\n{cmds}\n```", color=COR_TERMINAL)
            embed.set_footer(text=f"Fox Terminal {E_FOX}")
            await ch.send(embed=embed)
            return

    embed = discord.Embed(
        title=f"{E_FOX}  Fox Terminal — Ajuda Completa",
        description=(
            f"{E_SHIELD} **Cargo necessário:** <@&{CARGO_AUTORIZADO_ID}>\n"
            "Use todos os comandos **sem prefixo**, igual um terminal real!\n"
            f"Para ajuda específica: `help <comando>`"
        ),
        color=COR_TERMINAL,
        timestamp=datetime.now(timezone.utc)
    )

    campos = [
        (f"{E_PYTHON} Python / pip",
         "`pip install` `pip uninstall` `pip list` `pip show`\n"
         "`pip freeze` `pip search` `pip upgrade` `pip check`"),

        (f"{E_NODE} Node.js",
         "`npm install` `npm uninstall` `npm list` `npm run`\n"
         "`npx` `yarn add` `yarn remove` `pnpm install` `bun install`"),

        (f"{E_SYS} Sistema (apt)",
         "`apt install` `apt remove` `apt update` `apt upgrade`\n"
         "`apt search` `apt show` `apt autoremove` `apt list`"),

        (f"{E_PKG} Termux (pkg)",
         "`pkg install` `pkg uninstall` `pkg update` `pkg upgrade`\n"
         "`pkg search` `pkg show` `pkg list-installed` `pkg list-all`"),

        (f"{E_RUST} Rust / {E_RUBY} Ruby / {E_GO} Go",
         "`cargo install` `cargo build` `cargo run` `cargo test`\n"
         "`gem install` `gem list` `go install` `go build`"),

        (f"{E_JAVA} Java / {E_PHP} PHP",
         "`mvn package` `mvn clean` `gradle build`\n"
         "`composer require` `composer install` `composer update`"),

        (f"{E_GIT} Git",
         "`git clone` `git status` `git add` `git commit`\n"
         "`git push` `git pull` `git diff` `git branch` `git stash`"),

        (f"{E_FOLDER} Canais Discord",
         "`mkdir <nome>` → cria canal em TERMINAL\n"
         "`ls` → lista canais  `rm <nome>` → deleta canal  `cd` → ir ao canal"),

        (f"{E_TERM} Shell básico",
         "`pwd` `echo` `cat` `touch` `mv` `cp` `grep` `find` `wc`\n"
         "`head` `tail` `sort` `awk` `sed` `chmod` `which` `locate`"),

        (f"{E_GEAR} Sistema / processo",
         "`ps` `kill` `top` `df` `du` `free` `uptime` `date`\n"
         "`env` `export VAR=val` `unset VAR` `history` `clear`"),

        (f"{E_NET} Rede",
         "`curl <url>` `wget <url>` `ping <host>` `netstat`\n"
         "`ss` `ifconfig` `ip addr` `nmap` `traceroute` `dig`"),

        (f"{E_DOCKER} Docker",
         "`docker build` `docker run` `docker ps` `docker images`\n"
         "`docker pull` `docker stop` `docker rm` `docker rmi`"),

        (f"ℹ️ Info",
         "`whoami` `id` `uname` `uptime` `date` `cal`\n"
         "`lscpu` `lsblk` `df -h` `free -h`"),
    ]

    for title, value in campos:
        embed.add_field(name=title, value=value, inline=False)

    embed.set_footer(text=f"Fox Terminal {E_FOX}  •  Sem prefixo necessário!  •  {now_str()}")
    await ch.send(embed=embed)


# ══════════════════════════════════════════════════════════════════════════════
#  EVENTO PRINCIPAL — on_message
# ══════════════════════════════════════════════════════════════════════════════
@bot.event
async def on_ready():
    print(f"\n{'═'*55}")
    print(f"  {E_FOX}  Fox Terminal Bot v3.0 — ONLINE")
    print(f"  Usuário  : {bot.user.name}#{bot.user.discriminator}")
    print(f"  ID       : {bot.user.id}")
    print(f"  Servidores: {len(bot.guilds)}")
    print(f"  Cargo ID : {CARGO_AUTORIZADO_ID}")
    print(f"{'═'*55}\n")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"o terminal {E_FOX} | help"
        )
    )


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    content = message.content.strip()
    if not content:
        return

    if not is_terminal_cmd(content):
        await bot.process_commands(message)
        return

    # ── Verificação de cargo ────────────────────────────────────────────────
    if not await checar_cargo(message):
        return

    cmd, sub, full = parse_cmd(content)
    record_history(message.channel.id, full, message.author.display_name)

    # ── Roteamento ──────────────────────────────────────────────────────────
    try:
        # Python
        if cmd in ("pip", "pip3"):
            await handle_pip(message, sub)

        elif cmd in ("conda", "pipenv", "poetry"):
            await handle_generic_pm(message, cmd, sub, E_PYTHON, INSTALL_TIMEOUT)

        # Node.js
        elif cmd in ("npm", "npx", "node"):
            await handle_node_pm(message, cmd, sub)

        elif cmd in ("yarn", "pnpm", "bun"):
            await handle_node_pm(message, cmd, sub)

        # Sistema
        elif cmd in ("apt", "apt-get", "apt-cache"):
            await handle_apt(message, sub, cmd)

        elif cmd == "dpkg":
            out, err, code = run_cmd_fast(f"dpkg {' '.join(sub)} 2>&1", 30)
            await message.channel.send(embed=discord.Embed(
                title=f"{E_SYS} dpkg",
                description=f"```\n{truncate(out or err)}\n```",
                color=COR_OK if code == 0 else COR_ERRO
            ))

        elif cmd == "snap":
            loader = await AnimatedLoader(
                message.channel, f"snap {sub[0] if sub else ''}...",
                cmd_str=f"snap {' '.join(sub)}"
            ).start()
            loop = asyncio.get_event_loop()
            out, err, code = await loop.run_in_executor(
                None, lambda: run_cmd_fast(f"snap {' '.join(sub)} 2>&1", 120)
            )
            if code == 0: await loader.stop_ok("snap", truncate(out or "OK"))
            else:         await loader.stop_err("Erro: snap", truncate(err or out))

        # Termux
        elif cmd == "pkg":
            await handle_pkg(message, sub)

        # Rust
        elif cmd in ("cargo", "rustup"):
            await handle_generic_pm(message, cmd, sub, E_RUST, 300)

        # Ruby
        elif cmd in ("gem", "bundle", "rails"):
            await handle_generic_pm(message, cmd, sub, E_RUBY, INSTALL_TIMEOUT)

        # Go
        elif cmd == "go":
            await handle_generic_pm(message, cmd, sub, E_GO, INSTALL_TIMEOUT)

        # Java
        elif cmd in ("mvn", "gradle", "javac"):
            await handle_generic_pm(message, cmd, sub, E_JAVA, 180)

        # PHP
        elif cmd in ("composer", "php"):
            await handle_generic_pm(message, cmd, sub, E_PHP, INSTALL_TIMEOUT)

        # Git
        elif cmd == "git":
            await handle_git(message, sub)

        # Docker
        elif cmd in ("docker", "docker-compose"):
            await handle_docker(message, sub)

        # Banco de dados
        elif cmd in ("mysql", "psql", "sqlite3", "mongo", "redis-cli"):
            cmd_str = f"{cmd} {' '.join(sub)} 2>&1"
            out, err, code = run_cmd_fast(cmd_str, 15)
            await message.channel.send(embed=discord.Embed(
                title=f"{E_DB} {cmd}",
                description=f"```\n{truncate(out or err or '(sem saída)')}\n```",
                color=COR_OK if code == 0 else COR_AVISO
            ))

        # Canais Discord
        elif cmd == "mkdir":
            await handle_mkdir(message, sub)

        elif cmd in ("ls", "ll", "la"):
            await handle_ls(message, sub)

        elif cmd == "rm":
            await handle_rm(message, sub)

        elif cmd == "pwd":
            await handle_pwd(message)

        elif cmd == "echo":
            await handle_echo(message, sub)

        elif cmd in ("clear", "cls"):
            await handle_clear(message)

        # Shell
        elif cmd == "env":
            await handle_env(message)

        elif cmd == "export":
            await handle_export(message, sub)

        elif cmd == "history":
            await handle_history(message)

        elif cmd == "whoami":
            await handle_whoami(message)

        elif cmd in ("uname", "lscpu", "lsblk"):
            await handle_uname(message)

        elif cmd == "ps":
            await handle_ps(message)

        elif cmd == "df":
            await handle_df(message)

        elif cmd in ("free", "du"):
            await handle_free(message)

        elif cmd == "uptime":
            await handle_uptime(message)

        elif cmd == "date":
            await handle_date(message)

        elif cmd == "grep":
            await handle_grep(message, sub)

        elif cmd == "find":
            await handle_find(message, sub)

        elif cmd in ("curl", "wget"):
            await handle_curl_wget(message, cmd, sub)

        elif cmd in ("touch", "ln"):
            nome = sub[0] if sub else "arquivo"
            await message.channel.send(embed=discord.Embed(
                title=f"{E_OK} {cmd}",
                description=f"`{nome}` criado (simulado no Discord).", color=COR_OK
            ))

        elif cmd in ("mv", "cp"):
            if len(sub) >= 2:
                await message.channel.send(embed=discord.Embed(
                    title=f"{E_OK} {cmd}",
                    description=f"`{sub[0]}` → `{sub[1]}`\n*(operação simulada)*", color=COR_OK
                ))
            else:
                await message.channel.send(embed=discord.Embed(
                    description=f"```bash\n{cmd} <origem> <destino>\n```", color=COR_ERRO
                ))

        elif cmd in ("chmod", "chown"):
            await message.channel.send(embed=discord.Embed(
                title=f"{E_OK} {cmd}",
                description=f"Permissão alterada (simulado).", color=COR_OK
            ))

        elif cmd in ("kill", "killall"):
            pid = sub[0] if sub else "?"
            await message.channel.send(embed=discord.Embed(
                title=f"{E_OK} kill",
                description=f"Processo `{pid}` encerrado (simulado).", color=COR_AVISO
            ))

        elif cmd in ("head", "tail"):
            if sub:
                cmd_str = f"{cmd} {' '.join(sub)} 2>/dev/null"
                out, err, code = run_cmd_fast(cmd_str, 10)
                await message.channel.send(embed=discord.Embed(
                    title=f"📄 {cmd}", description=f"```\n{truncate(out or err)}\n```",
                    color=COR_OK if code == 0 else COR_ERRO
                ))

        elif cmd in ("wc", "sort", "uniq"):
            cmd_str = f"{cmd} {' '.join(sub)} 2>/dev/null"
            out, err, _ = run_cmd_fast(cmd_str, 10)
            await message.channel.send(embed=discord.Embed(
                title=f"📊 {cmd}", description=f"```\n{truncate(out or err)}\n```",
                color=COR_INFO
            ))

        elif cmd in ("which", "whereis", "locate"):
            cmd_str = f"{cmd} {' '.join(sub)} 2>/dev/null"
            out, err, code = run_cmd_fast(cmd_str, 10)
            await message.channel.send(embed=discord.Embed(
                title=f"🔍 {cmd}", description=f"```\n{truncate(out or err or 'Não encontrado.')}\n```",
                color=COR_OK if code == 0 else COR_AVISO
            ))

        elif cmd in ("ping",):
            host    = sub[0] if sub else "8.8.8.8"
            cmd_str = f"ping -c 4 {host} 2>&1"
            loader  = await AnimatedLoader(
                message.channel, f"ping {host}...", cmd_str=cmd_str
            ).start()
            loop = asyncio.get_event_loop()
            out, err, code = await loop.run_in_executor(
                None, lambda: run_cmd_fast(cmd_str, 15)
            )
            if code == 0:
                await loader.stop_ok(f"ping {host}", truncate(out))
            else:
                await loader.stop_err(f"ping {host}", truncate(err or out))

        elif cmd in ("netstat", "ss", "ifconfig", "ip"):
            cmd_str = f"{cmd} {' '.join(sub)} 2>&1"
            out, err, _ = run_cmd_fast(cmd_str, 10)
            await message.channel.send(embed=discord.Embed(
                title=f"{E_NET} {cmd}",
                description=f"```\n{truncate(out or err)}\n```", color=COR_INFO
            ))

        elif cmd in ("nmap", "traceroute", "nslookup", "dig", "host"):
            cmd_str = f"{cmd} {' '.join(sub)} 2>&1"
            loader  = await AnimatedLoader(
                message.channel, f"{E_NET} {cmd}...", cmd_str=cmd_str
            ).start()
            loop = asyncio.get_event_loop()
            out, err, code = await loop.run_in_executor(
                None, lambda: run_cmd_fast(cmd_str, 30)
            )
            if code == 0:
                await loader.stop_ok(f"{cmd}", truncate(out))
            else:
                await loader.stop_err(f"Erro: {cmd}", truncate(err or out))

        elif cmd in ("nano", "vim", "vi", "code"):
            await message.channel.send(embed=discord.Embed(
                title=f"{E_TERM} {cmd} (simulado)",
                description=(
                    f"Editores de texto não funcionam no modo interativo do Discord.\n"
                    f"Use `cat <arquivo>` para ler, ou `echo 'conteúdo' > arquivo` para escrever."
                ),
                color=COR_AVISO
            ))

        elif cmd in ("man", "info"):
            topic = sub[0] if sub else ""
            if topic:
                out, err, code = run_cmd_fast(f"man {topic} 2>&1 | head -30 | col -bx")
                await message.channel.send(embed=discord.Embed(
                    title=f"📖 man {topic}",
                    description=f"```\n{truncate(out or err or 'Página não encontrada.')}\n```",
                    color=COR_INFO
                ))

        elif cmd in ("help", "--help", "-h", "fox", "fox-help"):
            await handle_help(message, sub)

        # Comando desconhecido — tenta executar no sistema
        else:
            cmd_str = full
            loader  = await AnimatedLoader(
                message.channel, f"$ {cmd}", cmd_str=cmd_str
            ).start()
            loop = asyncio.get_event_loop()
            out, err, code = await loop.run_in_executor(
                None, lambda: run_cmd_fast(cmd_str + " 2>&1", CMD_TIMEOUT)
            )
            output = out or err or "(sem saída)"
            if code == 0:
                await loader.stop_ok(f"$ {cmd}", truncate(output))
            else:
                await loader.stop_err(f"Erro: $ {cmd}", truncate(output))

    except Exception as e:
        await message.channel.send(embed=discord.Embed(
            title=f"{E_ERR} Erro interno",
            description=f"```\n{str(e)[:500]}\n```",
            color=COR_ERRO
        ))

    await bot.process_commands(message)


# ══════════════════════════════════════════════════════════════════════════════
#  TASK — Status rotativo do bot
# ══════════════════════════════════════════════════════════════════════════════
STATUS_LIST = [
    (discord.ActivityType.watching,  f"o terminal {E_FOX}"),
    (discord.ActivityType.playing,   f"pip install tudo"),
    (discord.ActivityType.listening, f"git push origin main"),
    (discord.ActivityType.watching,  f"help para ajuda"),
    (discord.ActivityType.playing,   f"npm install fox-terminal"),
    (discord.ActivityType.watching,  f"pkg install python"),
]
_status_idx = 0

@tasks.loop(seconds=30)
async def rotate_status():
    global _status_idx
    typ, name = STATUS_LIST[_status_idx % len(STATUS_LIST)]
    await bot.change_presence(activity=discord.Activity(type=typ, name=name))
    _status_idx += 1

@bot.event
async def on_ready():
    print(f"\n{'═'*55}")
    print(f"  {E_FOX}  Fox Terminal Bot v3.0 — ONLINE!")
    print(f"  User     : {bot.user}")
    print(f"  Servidores: {len(bot.guilds)}")
    print(f"  Cargo    : {CARGO_AUTORIZADO_ID}")
    print(f"{'═'*55}\n")
    rotate_status.start()


# ══════════════════════════════════════════════════════════════════════════════
#  INICIAR
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    if BOT_TOKEN == os.environ.get('BOT_TOKEN')
        print(f"\n{E_ERR} ERRO: Substitua SEU_TOKEN_AQUI pelo seu token real!\n")
        sys.exit(1)
    print(f"{E_ROCKET} Iniciando Fox Terminal Bot...")
    bot.run(BOT_TOKEN)
