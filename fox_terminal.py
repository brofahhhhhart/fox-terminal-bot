import discord
from discord.ext import commands, tasks
import asyncio
import subprocess
import sys
import os
import re
import json
import time
import random
from datetime import datetime, timezone

# ─── CONFIG ───────────────────────────────────────────────────────────────────
# O token vem da variável de ambiente (nunca coloque o token direto aqui!)
TOKEN              = os.environ.get("DISCORD_TOKEN", "")
CARGO_ID           = 1465895263582294271   # único cargo que pode usar o bot
CATEGORIA          = "TERMINAL"
LOG_CANAL          = "fox-logs"
INSTALL_TIMEOUT    = 120
CMD_TIMEOUT        = 30

# ─── CORES ────────────────────────────────────────────────────────────────────
C_OK      = 0x2ECC71
C_ERRO    = 0xE74C3C
C_INFO    = 0x3498DB
C_LOADING = 0xF39C12
C_TERM    = 0x1ABC9C
C_AVISO   = 0xF1C40F
C_LOCK    = 0xC0392B

# ─── ESTADO ───────────────────────────────────────────────────────────────────
historico: dict[int, list] = {}
env_vars:  dict[int, dict] = {}
boot_time  = time.time()

# ─── BOT ──────────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.guilds           = True
intents.members          = True
bot = commands.Bot(command_prefix="!!interno__", intents=intents, help_command=None)

# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def agora():
    return datetime.now().strftime("%H:%M:%S")

def uptime():
    s = int(time.time() - boot_time)
    h, r = divmod(s, 3600); m, s = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def cortar(text: str, n=3500) -> str:
    text = (text or "").strip()
    if len(text) <= n:
        return text
    return text[:n] + f"\n... [{len(text)-n} chars omitidos]"

def tem_cargo(member: discord.Member) -> bool:
    return any(r.id == CARGO_ID for r in member.roles)

def rodar(cmd: str, timeout=CMD_TIMEOUT) -> tuple[str, str, int]:
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout,
            env={**os.environ, "DEBIAN_FRONTEND": "noninteractive",
                 "PIP_NO_INPUT": "1", "PYTHONDONTWRITEBYTECODE": "1"}
        )
        return r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired:
        return "", f"Tempo limite ({timeout}s) excedido.", 1
    except Exception as e:
        return "", str(e), 1

async def rodar_async(cmd: str, timeout=CMD_TIMEOUT):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: rodar(cmd, timeout))

async def get_categoria(guild):
    cat = discord.utils.get(guild.categories, name=CATEGORIA)
    if not cat:
        cat = await guild.create_category(CATEGORIA)
    return cat

async def logar(guild, autor, cmd, status):
    try:
        cat   = await get_categoria(guild)
        canal = discord.utils.get(guild.text_channels, name=LOG_CANAL)
        if not canal:
            canal = await guild.create_text_channel(LOG_CANAL, category=cat)
        e = discord.Embed(color=C_OK if "ok" in status.lower() else C_ERRO,
                          timestamp=datetime.now(timezone.utc))
        e.add_field(name="Usuário",  value=f"`{autor}`",      inline=True)
        e.add_field(name="Comando",  value=f"`{cmd[:80]}`",   inline=True)
        e.add_field(name="Status",   value=f"`{status}`",     inline=True)
        e.set_footer(text="Fox Terminal 🦊")
        await canal.send(embed=e)
    except Exception:
        pass

def salvar_hist(ch_id, cmd, autor):
    if ch_id not in historico:
        historico[ch_id] = []
    historico[ch_id].append({"cmd": cmd, "hora": agora(), "autor": autor})
    historico[ch_id] = historico[ch_id][-50:]

# ══════════════════════════════════════════════════════════════════════════════
#  LOADING ANIMADO
# ══════════════════════════════════════════════════════════════════════════════
BLOCOS    = ["░░░░░░░░░░", "█░░░░░░░░░", "██░░░░░░░░", "███░░░░░░░",
             "████░░░░░░", "█████░░░░░", "██████░░░░", "███████░░░",
             "████████░░", "█████████░", "██████████"]
SPIN      = ["◐", "◓", "◑", "◒"]
FASES     = ["Preparando...", "Executando...", "Processando...",
             "Quase pronto...", "Finalizando..."]

class Loader:
    def __init__(self, canal, titulo, cmd_str="", pkg=""):
        self.canal   = canal
        self.titulo  = titulo
        self.cmd_str = cmd_str
        self.pkg     = pkg
        self.msg     = None
        self._stop   = False
        self._task   = None
        self._inicio = time.time()

    def _tempo(self):
        return f"{time.time() - self._inicio:.1f}s"

    def _embed(self, frame):
        spin  = SPIN[frame % 4]
        bloco = BLOCOS[min(frame, 10)]
        pct   = min(frame * 10, 95)
        fase  = FASES[min(frame // 2, len(FASES) - 1)]

        desc = (
            f"```\n"
            f"{spin} {fase}\n"
            f"[{bloco}] {pct}%\n"
            f"⏱ {self._tempo()}\n"
            f"```"
        )
        e = discord.Embed(title=f"⏳  {self.titulo}", description=desc,
                          color=C_LOADING, timestamp=datetime.now(timezone.utc))
        if self.cmd_str:
            e.add_field(name="💻 Comando",
                        value=f"```bash\n{self.cmd_str[:180]}\n```", inline=False)
        if self.pkg:
            e.add_field(name="📦 Pacote", value=f"`{self.pkg}`", inline=True)
        e.add_field(name="⏱ Tempo", value=f"`{self._tempo()}`", inline=True)
        e.set_footer(text=f"Fox Terminal 🦊  •  {agora()}")
        return e

    async def start(self):
        self.msg  = await self.canal.send(embed=self._embed(0))
        self._task = asyncio.create_task(self._animar())
        return self

    async def _animar(self):
        await asyncio.sleep(0.8)
        frame = 1
        while not self._stop:
            try:
                await self.msg.edit(embed=self._embed(frame))
            except Exception:
                break
            frame += 1
            await asyncio.sleep(1.1)

    async def ok(self, titulo, saida, extra=None):
        self._stop = True
        if self._task:
            self._task.cancel()
        await asyncio.sleep(0.1)
        e = discord.Embed(title=f"✅  {titulo}", color=C_OK,
                          timestamp=datetime.now(timezone.utc))
        if saida.strip():
            e.description = f"```ansi\n{cortar(saida, 2000)}\n```"
        e.add_field(name="⏱ Tempo", value=f"`{self._tempo()}`", inline=True)
        e.add_field(name="🔥 Status", value="`Sucesso`", inline=True)
        if self.pkg:
            e.add_field(name="📦 Pacote", value=f"`{self.pkg}`", inline=True)
        if extra:
            for k, v in extra.items():
                e.add_field(name=k, value=str(v)[:512], inline=True)
        if self.cmd_str:
            e.add_field(name="💻 Executado",
                        value=f"```bash\n{self.cmd_str[:180]}\n```", inline=False)
        e.set_footer(text=f"Fox Terminal 🦊  •  {agora()}")
        try:
            await self.msg.edit(embed=e)
        except Exception:
            await self.canal.send(embed=e)

    async def erro(self, titulo, saida):
        self._stop = True
        if self._task:
            self._task.cancel()
        await asyncio.sleep(0.1)
        e = discord.Embed(title=f"❌  {titulo}", color=C_ERRO,
                          description=f"```\n{cortar(saida, 2500)}\n```" if saida.strip() else "",
                          timestamp=datetime.now(timezone.utc))
        e.add_field(name="⏱ Tempo",  value=f"`{self._tempo()}`", inline=True)
        e.add_field(name="⚠️ Status", value="`Falhou`",            inline=True)
        if self.cmd_str:
            e.add_field(name="💻 Comando",
                        value=f"```bash\n{self.cmd_str[:180]}\n```", inline=False)
        e.set_footer(text=f"Fox Terminal 🦊  •  {agora()}")
        try:
            await self.msg.edit(embed=e)
        except Exception:
            await self.canal.send(embed=e)

# ══════════════════════════════════════════════════════════════════════════════
#  DETECÇÃO DE COMANDOS SEM PREFIXO
# ══════════════════════════════════════════════════════════════════════════════
CMDS = {
    "pip","pip3","python","python3","conda","pipenv","poetry",
    "npm","npx","yarn","pnpm","bun","node",
    "apt","apt-get","apt-cache","dpkg","snap","flatpak",
    "pkg",
    "cargo","rustup","gem","bundle","go","mvn","gradle","composer","php",
    "git",
    "docker","docker-compose",
    "mkdir","ls","ll","la","pwd","cd","rm","cat","echo","touch","mv","cp",
    "chmod","chown","ln","head","tail","grep","wc","find","which","sort","awk",
    "clear","cls","history","env","export","unset",
    "ps","kill","killall","df","du","free","uptime","date","top",
    "curl","wget","ping","netstat","ss","ifconfig","ip","nmap","traceroute","dig",
    "whoami","uname","id","groups","lscpu","lsblk",
    "nano","vim","vi",
    "help","--help","-h","fox","man",
}

def eh_cmd_terminal(content: str) -> bool:
    first = content.strip().split()[0].lower() if content.strip() else ""
    return re.split(r"\d", first)[0] in CMDS

def parsear(content: str):
    parts = content.strip().split()
    return (parts[0].lower(), parts[1:], content.strip()) if parts else ("", [], "")

# ══════════════════════════════════════════════════════════════════════════════
#  MAPEAMENTO PKG (Termux → apt)
# ══════════════════════════════════════════════════════════════════════════════
PKG_MAP = {
    "python":"python3","python3":"python3","nodejs":"nodejs","nodejs-lts":"nodejs",
    "git":"git","vim":"vim","nano":"nano","curl":"curl","wget":"wget",
    "cmake":"cmake","clang":"clang","openssh":"openssh-client","ffmpeg":"ffmpeg",
    "lua54":"lua5.4","lua53":"lua5.3","ruby":"ruby","golang":"golang",
    "rust":"rustc","sqlite":"sqlite3","mysql":"mysql-client","php":"php",
    "java":"default-jdk","zip":"zip","unzip":"unzip","tar":"tar","htop":"htop",
    "tree":"tree","jq":"jq","tmux":"tmux","screen":"screen","neovim":"neovim",
    "zsh":"zsh","fish":"fish","imagemagick":"imagemagick","pandoc":"pandoc",
    "R":"r-base","perl":"perl","redis":"redis","nginx":"nginx","apache2":"apache2",
    "postgresql":"postgresql","openjdk-11":"openjdk-11-jdk",
    "openjdk-17":"openjdk-17-jdk","openjdk-21":"openjdk-21-jdk",
    "dotnet":"dotnet-sdk-8","docker":"docker.io","make":"make","gcc":"gcc",
    "g++":"g++","gdb":"gdb","valgrind":"valgrind","strace":"strace",
    "netcat":"netcat","nmap":"nmap","wireshark":"wireshark","tcpdump":"tcpdump",
    "fzf":"fzf","bat":"bat","ripgrep":"ripgrep","fd":"fd-find","exa":"exa",
    "lsd":"lsd","delta":"git-delta","lazygit":"lazygit","gh":"gh",
}

PKG_PIP_POPULARES = [
    "requests","numpy","pandas","matplotlib","flask","fastapi","django",
    "sqlalchemy","aiohttp","httpx","pydantic","celery","redis","pymongo",
    "discord.py","selenium","playwright","beautifulsoup4","scrapy","tqdm",
    "rich","click","typer","loguru","python-dotenv","pytest","black",
    "torch","tensorflow","scikit-learn","opencv-python","Pillow","scipy",
]

# ══════════════════════════════════════════════════════════════════════════════
#  HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

# ── PIP ───────────────────────────────────────────────────────────────────────
async def h_pip(msg: discord.Message, sub: list):
    ch = msg.channel
    if not sub:
        e = discord.Embed(title="🐍 pip — Python", color=0x3776AB)
        e.add_field(name="Comandos",
            value=("`pip install <pkg>` `pip install <pkg>==<ver>`\n"
                   "`pip uninstall <pkg>` `pip list` `pip show <pkg>`\n"
                   "`pip freeze` `pip search <pkg>` `pip upgrade <pkg>`\n"
                   "`pip check` `pip install -r requirements.txt`"), inline=False)
        e.add_field(name="⭐ Populares",
            value="`"+"` `".join(random.sample(PKG_PIP_POPULARES,8))+"`", inline=False)
        await ch.send(embed=e); return

    action = sub[0].lower()
    args   = sub[1:]

    if action == "install" and args:
        pkg = " ".join(args)
        loader = await Loader(ch, f"Instalando {pkg}",
                              f"pip install {pkg} --prefer-binary", pkg).start()
        out, err, code = await rodar_async(
            f"{sys.executable} -m pip install {pkg} "
            f"--no-cache-dir -q -q --disable-pip-version-check --prefer-binary",
            INSTALL_TIMEOUT)
        if code == 0:
            # pega versão
            vout, _, _ = await rodar_async(
                f"{sys.executable} -m pip show {args[0].split('==')[0]} 2>/dev/null")
            versao = next((l.split(':',1)[1].strip()
                           for l in vout.splitlines() if l.startswith("Version:")), "?")
            await loader.ok(f"Instalado: {pkg}", out or "OK!",
                            extra={"🏷️ Versão": f"`{versao}`"})
            await logar(msg.guild, msg.author.display_name, f"pip install {pkg}", f"OK v{versao}")
        else:
            await loader.erro(f"Erro: pip install {pkg}", err or out)

    elif action == "uninstall" and args:
        pkg = " ".join(args)
        loader = await Loader(ch, f"Removendo {pkg}", f"pip uninstall {pkg} -y").start()
        out, err, code = await rodar_async(
            f"{sys.executable} -m pip uninstall {pkg} -y "
            f"--disable-pip-version-check", 60)
        if code == 0: await loader.ok(f"Removido: {pkg}", out or "OK!")
        else:         await loader.erro(f"Erro ao remover {pkg}", err or out)

    elif action == "list":
        loader = await Loader(ch, "Listando pacotes...").start()
        out, _, _ = await rodar_async(f"{sys.executable} -m pip list --format=columns")
        total = max(0, len(out.strip().splitlines()) - 2)
        await loader.ok(f"Pacotes instalados", cortar(out),
                        extra={"📊 Total": f"`{total}`"})

    elif action == "show" and args:
        loader = await Loader(ch, f"Info: {args[0]}").start()
        out, err, code = await rodar_async(f"{sys.executable} -m pip show {args[0]}")
        if code == 0: await loader.ok(f"📦 {args[0]}", out)
        else:         await loader.erro(f"Não encontrado: {args[0]}", f"Tente `pip install {args[0]}`")

    elif action == "freeze":
        loader = await Loader(ch, "pip freeze...").start()
        out, _, _ = await rodar_async(f"{sys.executable} -m pip freeze")
        await loader.ok("pip freeze", cortar(out))

    elif action == "search" and args:
        q = args[0].lower()
        m = [p for p in PKG_PIP_POPULARES if q in p.lower()]
        desc = "```\n"+"\n".join(m[:20])+"```" if m else f"Nenhum resultado para `{q}`."
        await ch.send(embed=discord.Embed(title=f"🔍 pip search: {q}",
                                          description=desc, color=0x3776AB))

    elif action in ("upgrade","update") and args:
        pkg = args[0]
        loader = await Loader(ch, f"Atualizando {pkg}",
                              f"pip install --upgrade {pkg} --prefer-binary", pkg).start()
        out, err, code = await rodar_async(
            f"{sys.executable} -m pip install --upgrade {pkg} "
            f"--no-cache-dir -q --prefer-binary", INSTALL_TIMEOUT)
        if code == 0: await loader.ok(f"Atualizado: {pkg}", out or "OK!")
        else:         await loader.erro(f"Erro ao atualizar {pkg}", err or out)

    elif action == "check":
        loader = await Loader(ch, "Verificando dependências...").start()
        out, err, code = await rodar_async(f"{sys.executable} -m pip check")
        if code == 0: await loader.ok("Sem conflitos!", out or "Tudo OK.")
        else:         await loader.erro("Conflitos encontrados", err or out)

    else:
        cmd_str = f"{sys.executable} -m pip {' '.join(sub)}"
        loader  = await Loader(ch, f"pip {action}...", cmd_str).start()
        out, err, code = await rodar_async(cmd_str, INSTALL_TIMEOUT)
        if code == 0: await loader.ok(f"pip {action}", cortar(out or "OK"))
        else:         await loader.erro(f"Erro: pip {action}", cortar(err or out))

# ── NODE.JS (npm/yarn/pnpm/bun) ───────────────────────────────────────────────
async def h_node(msg: discord.Message, cmd: str, sub: list):
    ch = msg.channel
    if not sub:
        e = discord.Embed(title=f"🟢 {cmd}", color=0x68A063)
        e.add_field(name="Comandos",
            value=(f"`{cmd} install <pkg>` `{cmd} uninstall <pkg>`\n"
                   f"`{cmd} list` `{cmd} run <script>` `{cmd} init`\n"
                   f"`{cmd} update <pkg>` `{cmd} outdated`"), inline=False)
        await ch.send(embed=e); return

    pkg    = sub[1] if len(sub) > 1 else ""
    cmd_str = f"{cmd} {' '.join(sub)}"
    loader  = await Loader(ch, f"{cmd} {sub[0]}...", cmd_str, pkg).start()
    out, err, code = await rodar_async(cmd_str, INSTALL_TIMEOUT)
    if code == 0: await loader.ok(f"{cmd} {sub[0]}", cortar(out or "OK"))
    else:
        emsg = err or out
        if "not found" in emsg.lower():
            emsg = f"`{cmd}` não encontrado. Instale: `apt install nodejs npm`\n\n{emsg}"
        await loader.erro(f"Erro: {cmd} {sub[0]}", cortar(emsg))

# ── APT ───────────────────────────────────────────────────────────────────────
async def h_apt(msg: discord.Message, sub: list, base="apt-get"):
    ch = msg.channel
    if not sub:
        e = discord.Embed(title="⚙️ apt — Sistema", color=C_INFO)
        e.add_field(name="Comandos",
            value=("`apt install <pkg>` `apt remove <pkg>`\n"
                   "`apt update` `apt upgrade` `apt search <pkg>`\n"
                   "`apt show <pkg>` `apt list --installed` `apt autoremove`"), inline=False)
        await ch.send(embed=e); return

    action  = sub[0].lower()
    pkg_str = " ".join(sub[1:])

    if action in ("install","remove","purge","reinstall") and pkg_str:
        loader = await Loader(ch, f"apt {action} {pkg_str}",
                              f"sudo {base} {action} {pkg_str} -y", pkg_str).start()
        out, err, code = await rodar_async(f"sudo {base} {action} {pkg_str} -y 2>&1", 180)
        if code == 0: await loader.ok(f"apt {action}: {pkg_str}", cortar(out))
        else:         await loader.erro(f"Erro: apt {action} {pkg_str}", cortar(err or out))

    elif action in ("update","upgrade","full-upgrade"):
        loader = await Loader(ch, f"apt {action}...", f"sudo {base} {action} -y").start()
        out, err, code = await rodar_async(f"sudo {base} {action} -y 2>&1", 300)
        if code == 0: await loader.ok(f"apt {action} concluído", cortar(out))
        else:         await loader.erro(f"Erro: apt {action}", cortar(err or out))

    elif action == "search" and pkg_str:
        loader = await Loader(ch, f"Buscando {pkg_str}...").start()
        out, _, _ = await rodar_async(f"apt-cache search {pkg_str} 2>&1 | head -25")
        await loader.ok(f"apt search: {pkg_str}", cortar(out or "Nenhum resultado."))

    elif action in ("show","info") and pkg_str:
        loader = await Loader(ch, f"Info: {pkg_str}...").start()
        out, _, _ = await rodar_async(f"apt-cache show {pkg_str} 2>&1 | head -30")
        await loader.ok(f"apt show: {pkg_str}", cortar(out or "Não encontrado."))

    elif action == "autoremove":
        loader = await Loader(ch, "apt autoremove...", "sudo apt-get autoremove -y").start()
        out, err, code = await rodar_async("sudo apt-get autoremove -y 2>&1", 120)
        if code == 0: await loader.ok("apt autoremove concluído", cortar(out))
        else:         await loader.erro("Erro: apt autoremove", cortar(err or out))

    else:
        cmd_str = f"sudo {base} {' '.join(sub)} -y 2>&1"
        loader  = await Loader(ch, f"apt {action}...", cmd_str).start()
        out, err, code = await rodar_async(cmd_str, 180)
        if code == 0: await loader.ok(f"apt {action}", cortar(out or "OK"))
        else:         await loader.erro(f"Erro: apt {action}", cortar(err or out))

# ── PKG (Termux) ──────────────────────────────────────────────────────────────
async def h_pkg(msg: discord.Message, sub: list):
    ch = msg.channel
    if not sub:
        e = discord.Embed(title="📦 pkg — Termux", color=0x00BCD4)
        e.add_field(name="Comandos",
            value=("`pkg install <pkg>` `pkg uninstall <pkg>`\n"
                   "`pkg update` `pkg upgrade` `pkg search <pkg>`\n"
                   "`pkg list-installed` `pkg list-all` `pkg show <pkg>`"), inline=False)
        e.add_field(name="⭐ Disponíveis",
            value="`"+"` `".join(list(PKG_MAP.keys())[:18])+"`", inline=False)
        await ch.send(embed=e); return

    action = sub[0].lower()

    if action == "install" and len(sub) > 1:
        orig   = sub[1]
        apt_pkg = PKG_MAP.get(orig, orig)
        loader  = await Loader(ch, f"pkg install {orig}",
                               f"sudo apt-get install {apt_pkg} -y", orig).start()
        out, err, code = await rodar_async(
            f"sudo apt-get install {apt_pkg} -y 2>&1", 180)
        if code == 0:
            await loader.ok(f"Instalado: {orig}", cortar(out or "OK!"),
                            extra={"🐧 Termux": f"`{orig}`", "⚙️ apt": f"`{apt_pkg}`"})
        else:
            await loader.erro(f"Erro: pkg install {orig}", cortar(err or out))

    elif action in ("update","upgrade"):
        loader = await Loader(ch, f"pkg {action}...",
                              f"sudo apt-get {action} -y").start()
        out, err, code = await rodar_async(f"sudo apt-get {action} -y 2>&1", 300)
        if code == 0: await loader.ok(f"pkg {action} concluído", cortar(out))
        else:         await loader.erro(f"Erro: pkg {action}", cortar(err or out))

    elif action in ("uninstall","remove") and len(sub) > 1:
        apt_pkg = PKG_MAP.get(sub[1], sub[1])
        loader  = await Loader(ch, f"pkg uninstall {sub[1]}",
                               f"sudo apt-get remove {apt_pkg} -y").start()
        out, err, code = await rodar_async(f"sudo apt-get remove {apt_pkg} -y 2>&1", 60)
        if code == 0: await loader.ok(f"Removido: {sub[1]}", cortar(out))
        else:         await loader.erro(f"Erro ao remover {sub[1]}", cortar(err or out))

    elif action == "list-installed":
        loader = await Loader(ch, "Listando instalados...").start()
        out, _, _ = await rodar_async("dpkg -l 2>/dev/null | awk 'NR>5{print $2,$3}' | head -40")
        await loader.ok("Pacotes instalados", cortar(out))

    elif action == "list-all":
        pkgs = "\n".join(f"  {k:<22} → {v}" for k,v in list(PKG_MAP.items())[:40])
        await ch.send(embed=discord.Embed(
            title=f"📦 pkg list-all ({len(PKG_MAP)} pacotes)",
            description=f"```\n{'Termux':<22}   apt\n{'─'*45}\n{pkgs}\n```",
            color=0x00BCD4))

    elif action == "search" and len(sub) > 1:
        q = sub[1].lower()
        m = {k:v for k,v in PKG_MAP.items() if q in k.lower() or q in v.lower()}
        if m:
            r = "\n".join(f"  {k:<22} → {v}" for k,v in m.items())
            await ch.send(embed=discord.Embed(
                title=f"🔍 pkg search: {q}",
                description=f"```\n{r}\n```", color=0x00BCD4))
        else:
            await ch.send(embed=discord.Embed(
                description=f"Nenhum pacote para `{q}`.", color=C_AVISO))

    elif action == "show" and len(sub) > 1:
        apt_pkg = PKG_MAP.get(sub[1], sub[1])
        loader  = await Loader(ch, f"pkg show {sub[1]}...").start()
        out, _, _ = await rodar_async(f"apt-cache show {apt_pkg} 2>&1 | head -25")
        await loader.ok(f"pkg show: {sub[1]}", cortar(out or "Não encontrado."))

    else:
        cmd_str = "apt-get " + " ".join(sub) + " -y 2>&1"
        loader  = await Loader(ch, f"pkg {action}...", cmd_str).start()
        out, err, code = await rodar_async(cmd_str, 180)
        if code == 0: await loader.ok(f"pkg {action}", cortar(out or "OK"))
        else:         await loader.erro(f"Erro: pkg {action}", cortar(err or out))

# ── GIT ───────────────────────────────────────────────────────────────────────
async def h_git(msg: discord.Message, sub: list):
    ch = msg.channel
    if not sub:
        e = discord.Embed(title="🔀 git", color=0xF05032)
        e.add_field(name="Básico",
            value="`git clone <url>` `git init` `git status` `git log --oneline -10`", inline=False)
        e.add_field(name="Mudanças",
            value="`git add .` `git commit -m 'msg'` `git diff` `git stash`", inline=False)
        e.add_field(name="Remoto",
            value="`git push` `git pull` `git fetch` `git remote -v`", inline=False)
        e.add_field(name="Branches",
            value="`git branch` `git checkout <b>` `git merge <b>` `git rebase <b>` `git tag`", inline=False)
        await ch.send(embed=e); return

    action  = sub[0].lower()
    cmd_str = "git " + " ".join(sub)
    timeout = 120 if action in ("clone","push","pull","fetch") else 30
    loader  = await Loader(ch, f"git {action}...", cmd_str,
                           sub[1] if len(sub) > 1 else "").start()
    out, err, code = await rodar_async(cmd_str, timeout)
    output = out or err or "(sem saída)"
    if code == 0: await loader.ok(f"git {action}", cortar(output))
    else:         await loader.erro(f"Erro: git {action}", cortar(err or out))

# ── MKDIR (cria canal Discord) ────────────────────────────────────────────────
async def h_mkdir(msg: discord.Message, sub: list):
    ch = msg.channel
    if not sub:
        await ch.send(embed=discord.Embed(
            description="```bash\nmkdir <nome-do-canal>\n```\nCria canal na categoria TERMINAL.",
            color=C_INFO)); return

    nome = re.sub(r"[^a-z0-9\-]", "-", " ".join(sub).lower().strip()).strip("-")
    nome = re.sub(r"-{2,}", "-", nome)
    if not nome:
        await ch.send(embed=discord.Embed(
            description="❌ Nome inválido.", color=C_ERRO)); return

    loader = await Loader(ch, f"Criando canal #{nome}...", f"mkdir {nome}").start()
    try:
        cat = await get_categoria(msg.guild)
        if discord.utils.get(cat.channels, name=nome):
            await loader.erro("Canal já existe",
                              f"#{nome} já existe. Escolha outro nome."); return

        novo = await msg.guild.create_text_channel(
            name=nome, category=cat,
            topic=f"📁 Criado por {msg.author.display_name} via Fox Terminal • {agora()}")

        e = discord.Embed(title="✅  Canal criado!", color=C_OK,
                          timestamp=datetime.now(timezone.utc))
        e.add_field(name="📁 Canal",   value=novo.mention,   inline=True)
        e.add_field(name="📂 Categoria",value=f"`{CATEGORIA}`", inline=True)
        e.add_field(name="👤 Criado por",value=msg.author.mention, inline=True)
        e.set_footer(text="Fox Terminal 🦊  •  mkdir")
        loader._stop = True
        if loader._task: loader._task.cancel()
        await asyncio.sleep(0.1)
        await loader.msg.edit(embed=e)

        welcome = discord.Embed(
            title=f"📁  {nome}",
            description=(
                f"Canal criado por {msg.author.mention}.\n\n"
                f"```bash\n$ pwd\n/{CATEGORIA}/{nome}\n\n"
                f"$ echo 'Fox Terminal pronto!'\nFox Terminal pronto!\n```"
            ), color=C_TERM, timestamp=datetime.now(timezone.utc))
        welcome.set_footer(text=f"Fox Terminal 🦊  •  {agora()}")
        await novo.send(embed=welcome)
        await logar(msg.guild, msg.author.display_name, f"mkdir {nome}", "OK")

    except discord.Forbidden:
        await loader.erro("Sem permissão", "O bot precisa de **Gerenciar Canais**.")
    except Exception as e:
        await loader.erro("Erro ao criar canal", str(e))

# ── LS ────────────────────────────────────────────────────────────────────────
async def h_ls(msg: discord.Message):
    cat = discord.utils.get(msg.guild.categories, name=CATEGORIA)
    if not cat or not cat.channels:
        await msg.channel.send(embed=discord.Embed(
            description=f"Categoria `{CATEGORIA}` vazia. Use `mkdir <nome>`.",
            color=C_INFO)); return

    linhas = [f"total {len(cat.channels)}"]
    for c in sorted(cat.channels, key=lambda x: x.name):
        data = c.created_at.strftime("%b %d %H:%M") if c.created_at else "---"
        linhas.append(f"drwxr-xr-x  📁 {c.name:<30} {data}")

    await msg.channel.send(embed=discord.Embed(
        title=f"📁  /{CATEGORIA}",
        description="```\n" + "\n".join(linhas) + "\n```",
        color=C_INFO))

# ── RM ────────────────────────────────────────────────────────────────────────
async def h_rm(msg: discord.Message, sub: list):
    nome = sub[-1].lstrip("#") if sub else ""
    if not nome:
        await msg.channel.send(embed=discord.Embed(
            description="```bash\nrm <nome-do-canal>\n```", color=C_ERRO)); return

    cat  = discord.utils.get(msg.guild.categories, name=CATEGORIA)
    alvo = discord.utils.get(cat.channels, name=nome) if cat else None
    if not alvo:
        await msg.channel.send(embed=discord.Embed(
            description=f"❌ Canal `{nome}` não encontrado.", color=C_ERRO)); return

    loader = await Loader(msg.channel, f"rm {nome}...", f"rm -rf {nome}").start()
    try:
        await alvo.delete(reason=f"Fox Terminal rm por {msg.author}")
        await loader.ok(f"Removido: #{nome}", f"Canal deletado com sucesso.")
    except discord.Forbidden:
        await loader.erro("Sem permissão", "Preciso de **Gerenciar Canais**.")

# ── GENÉRICO ──────────────────────────────────────────────────────────────────
async def h_generico(msg: discord.Message, cmd: str, sub: list,
                     emoji="📦", timeout=INSTALL_TIMEOUT):
    cmd_str = f"{cmd} {' '.join(sub)}"
    pkg     = sub[1] if len(sub) > 1 else (sub[0] if sub else "")
    loader  = await Loader(msg.channel, f"{emoji} {cmd} {sub[0] if sub else ''}...",
                           cmd_str, pkg).start()
    out, err, code = await rodar_async(cmd_str, timeout)
    if code == 0:
        await loader.ok(f"{cmd} {sub[0] if sub else ''}", cortar(out or "OK"))
        await logar(msg.guild, msg.author.display_name, cmd_str, "OK")
    else:
        emsg = err or out
        if "not found" in emsg.lower():
            emsg = f"`{cmd}` não encontrado. Instale com `apt install` ou `pkg install`.\n\n{emsg}"
        await loader.erro(f"Erro: {cmd}", cortar(emsg))

# ── HELP ──────────────────────────────────────────────────────────────────────
async def h_help(msg: discord.Message):
    e = discord.Embed(
        title="🦊  Fox Terminal — Ajuda",
        description=(
            f"🛡️ Cargo necessário: <@&{CARGO_ID}>\n"
            "Use todos os comandos **sem prefixo**, igual um terminal real!"
        ),
        color=C_TERM, timestamp=datetime.now(timezone.utc))
    campos = [
        ("🐍 Python",  "`pip install` `pip uninstall` `pip list` `pip show` `pip freeze` `pip search` `pip upgrade` `pip check`"),
        ("🟢 Node.js", "`npm install` `npm run` `npx` `yarn add` `pnpm install` `bun install`"),
        ("⚙️ Sistema", "`apt install` `apt update` `apt upgrade` `apt search` `apt remove` `apt autoremove`"),
        ("📦 Termux",  "`pkg install` `pkg update` `pkg upgrade` `pkg search` `pkg list-installed` `pkg list-all`"),
        ("🦀🔴🐹",    "`cargo install` `gem install` `go install` `go build` `mvn package` `composer require`"),
        ("🔀 Git",     "`git clone` `git status` `git add` `git commit` `git push` `git pull` `git stash`"),
        ("📁 Canais",  "`mkdir <nome>` cria canal  |  `ls` lista  |  `rm <nome>` deleta"),
        ("💻 Shell",   "`pwd` `echo` `cat` `grep` `find` `ps` `df` `free` `uptime` `env` `export` `clear` `history`"),
        ("🌐 Rede",    "`curl <url>` `wget <url>` `ping <host>` `netstat` `ip addr` `nmap`"),
        ("ℹ️ Info",    "`whoami` `uname` `uptime` `date` `df -h` `free -h` `lscpu`"),
    ]
    for title, value in campos:
        e.add_field(name=title, value=value, inline=False)
    e.set_footer(text=f"Fox Terminal 🦊  •  uptime: {uptime()}")
    await msg.channel.send(embed=e)

# ══════════════════════════════════════════════════════════════════════════════
#  ON_MESSAGE — ROTEAMENTO PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
@bot.event
async def on_message(msg: discord.Message):
    if msg.author.bot or not msg.guild:
        return
    content = msg.content.strip()
    if not content or not eh_cmd_terminal(content):
        await bot.process_commands(msg); return

    # ── Verificação de cargo ─────────────────────────────────────────────────
    if not tem_cargo(msg.author):
        e = discord.Embed(
            title="🔒  Acesso Negado",
            description=(
                f"{msg.author.mention}, você **não tem permissão** para usar o Fox Terminal.\n"
                f"Cargo necessário: <@&{CARGO_ID}>"
            ), color=C_LOCK)
        await msg.channel.send(embed=e, delete_after=8)
        try: await msg.delete()
        except Exception: pass
        return

    cmd, sub, full = parsear(content)
    salvar_hist(msg.channel.id, full, msg.author.display_name)

    try:
        # Python
        if cmd in ("pip", "pip3"):
            await h_pip(msg, sub)
        elif cmd in ("conda","pipenv","poetry"):
            await h_generico(msg, cmd, sub, "🐍", INSTALL_TIMEOUT)
        # Node
        elif cmd in ("npm","npx","node"):
            await h_node(msg, cmd, sub)
        elif cmd in ("yarn","pnpm","bun"):
            await h_node(msg, cmd, sub)
        # Sistema
        elif cmd in ("apt","apt-get","apt-cache"):
            await h_apt(msg, sub, cmd)
        elif cmd == "dpkg":
            out, err, _ = await rodar_async(f"dpkg {' '.join(sub)} 2>&1", 15)
            await msg.channel.send(embed=discord.Embed(
                title="⚙️ dpkg",
                description=f"```\n{cortar(out or err)}\n```", color=C_INFO))
        elif cmd == "snap":
            loader = await Loader(msg.channel, f"snap {sub[0] if sub else ''}...",
                                  f"snap {' '.join(sub)}").start()
            out, err, code = await rodar_async(f"snap {' '.join(sub)} 2>&1", 120)
            if code == 0: await loader.ok("snap", cortar(out or "OK"))
            else:         await loader.erro("Erro: snap", cortar(err or out))
        # Termux
        elif cmd == "pkg":
            await h_pkg(msg, sub)
        # Outras linguagens
        elif cmd in ("cargo","rustup"):
            await h_generico(msg, cmd, sub, "🦀", 300)
        elif cmd in ("gem","bundle","rails"):
            await h_generico(msg, cmd, sub, "💎", INSTALL_TIMEOUT)
        elif cmd == "go":
            await h_generico(msg, cmd, sub, "🐹", INSTALL_TIMEOUT)
        elif cmd in ("mvn","gradle","javac"):
            await h_generico(msg, cmd, sub, "☕", 180)
        elif cmd in ("composer","php"):
            await h_generico(msg, cmd, sub, "🐘", INSTALL_TIMEOUT)
        # Git
        elif cmd == "git":
            await h_git(msg, sub)
        # Docker
        elif cmd in ("docker","docker-compose"):
            await h_generico(msg, cmd, sub, "🐳", 120)
        # Canais Discord
        elif cmd == "mkdir":
            await h_mkdir(msg, sub)
        elif cmd in ("ls","ll","la"):
            await h_ls(msg)
        elif cmd == "rm":
            await h_rm(msg, sub)
        elif cmd == "pwd":
            cat = msg.channel.category
            path = f"/{msg.guild.name}/{cat.name if cat else 'root'}/{msg.channel.name}"
            await msg.channel.send(embed=discord.Embed(
                title="📍 pwd", description=f"```\n{path}\n```", color=C_INFO))
        elif cmd == "echo":
            ev   = env_vars.get(msg.guild.id, {})
            txt  = " ".join(sub)
            for k, v in ev.items(): txt = txt.replace(f"${k}", v)
            await msg.channel.send(embed=discord.Embed(
                description=f"```\n{txt}\n```", color=C_INFO))
        elif cmd in ("clear","cls"):
            try:
                await msg.channel.purge(limit=50)
                m = await msg.channel.send(embed=discord.Embed(
                    title="✅ clear", description="50 mensagens apagadas.", color=C_OK))
                await asyncio.sleep(3)
                await m.delete()
            except discord.Forbidden:
                await msg.channel.send(embed=discord.Embed(
                    description="❌ Sem permissão para **Gerenciar Mensagens**.", color=C_ERRO))
        elif cmd == "env":
            ev = env_vars.get(msg.guild.id, {})
            desc = "```bash\n"+"\n".join(f"export {k}={v}" for k,v in ev.items())+"```" if ev else "Nenhuma variável. Use `export VAR=valor`"
            await msg.channel.send(embed=discord.Embed(
                title="🌿 env", description=desc, color=C_INFO))
        elif cmd == "export":
            raw = " ".join(sub)
            if "=" in raw:
                k, _, v = raw.partition("=")
                gid = msg.guild.id
                if gid not in env_vars: env_vars[gid] = {}
                env_vars[gid][k.strip()] = v.strip()
                await msg.channel.send(embed=discord.Embed(
                    title="✅ export",
                    description=f"```bash\nexport {k.strip()}={v.strip()}\n```", color=C_OK))
        elif cmd == "history":
            hist = historico.get(msg.channel.id, [])
            if not hist:
                await msg.channel.send(embed=discord.Embed(
                    description="Sem histórico.", color=C_INFO))
            else:
                lines = "\n".join(
                    f"{i+1:>3}  [{h['hora']}]  {h['autor']:<14}  {h['cmd']}"
                    for i, h in enumerate(hist[-25:]))
                await msg.channel.send(embed=discord.Embed(
                    title=f"📋 Histórico ({len(hist)})",
                    description=f"```\n{cortar(lines,1800)}\n```", color=C_INFO))
        elif cmd == "whoami":
            u = msg.author
            roles = [r.name for r in u.roles if r.name != "@everyone"]
            e = discord.Embed(title="👤 whoami", color=C_INFO,
                              timestamp=datetime.now(timezone.utc))
            e.add_field(name="Usuário", value=f"`{u.name}`",          inline=True)
            e.add_field(name="ID",      value=f"`{u.id}`",            inline=True)
            e.add_field(name="Apelido", value=f"`{u.display_name}`",  inline=True)
            e.add_field(name="Cargos",  value=", ".join(f"`{r}`" for r in roles[:5]) or "`—`", inline=False)
            e.set_thumbnail(url=u.display_avatar.url)
            await msg.channel.send(embed=e)
        elif cmd in ("uname","lscpu","lsblk"):
            out, _, _ = await rodar_async("uname -a && echo '---' && cat /etc/os-release 2>/dev/null | head -5")
            e = discord.Embed(title="💻 uname", color=C_INFO)
            e.add_field(name="Sistema", value=f"```{cortar(out,400)}```", inline=False)
            e.add_field(name="Python",  value=f"`{sys.version.split()[0]}`", inline=True)
            e.add_field(name="Bot uptime", value=f"`{uptime()}`",             inline=True)
            await msg.channel.send(embed=e)
        elif cmd == "ps":
            out, _, _ = await rodar_async("ps aux --sort=-%cpu 2>/dev/null | head -12")
            await msg.channel.send(embed=discord.Embed(
                title="⚙️ ps", description=f"```\n{cortar(out,1800)}\n```", color=C_INFO))
        elif cmd == "df":
            out, _, _ = await rodar_async("df -h 2>/dev/null")
            await msg.channel.send(embed=discord.Embed(
                title="💾 df", description=f"```\n{cortar(out,1500)}\n```", color=C_INFO))
        elif cmd in ("free","du"):
            out, _, _ = await rodar_async(f"{cmd} -h 2>/dev/null")
            await msg.channel.send(embed=discord.Embed(
                title=f"🧠 {cmd}", description=f"```\n{cortar(out,1200)}\n```", color=C_INFO))
        elif cmd == "uptime":
            out, _, _ = await rodar_async("uptime")
            e = discord.Embed(title="⏱ uptime", color=C_INFO)
            e.add_field(name="Sistema", value=f"```{out.strip()}```", inline=False)
            e.add_field(name="Bot",     value=f"`{uptime()}`",         inline=True)
            await msg.channel.send(embed=e)
        elif cmd in ("date","cal"):
            out, _, _ = await rodar_async(cmd)
            await msg.channel.send(embed=discord.Embed(
                title=f"📅 {cmd}", description=f"```\n{out.strip()}\n```", color=C_INFO))
        elif cmd == "grep":
            out, err, code = await rodar_async("grep " + " ".join(sub), 10)
            await msg.channel.send(embed=discord.Embed(
                title="🔍 grep",
                description=f"```\n{cortar(out or err or 'Sem resultado.')}\n```",
                color=C_OK if code == 0 else C_AVISO))
        elif cmd == "find":
            out, err, _ = await rodar_async("find " + " ".join(sub) + " 2>/dev/null | head -25", 15)
            await msg.channel.send(embed=discord.Embed(
                title="🔍 find", description=f"```\n{cortar(out or err)}\n```", color=C_INFO))
        elif cmd in ("which","whereis"):
            out, _, _ = await rodar_async(f"{cmd} {' '.join(sub)} 2>/dev/null")
            await msg.channel.send(embed=discord.Embed(
                title=f"🔍 {cmd}", description=f"```\n{cortar(out or 'Não encontrado.')}\n```", color=C_INFO))
        elif cmd in ("head","tail","wc","sort","awk","sed"):
            out, err, _ = await rodar_async(f"{cmd} {' '.join(sub)} 2>/dev/null", 10)
            await msg.channel.send(embed=discord.Embed(
                title=f"📄 {cmd}", description=f"```\n{cortar(out or err)}\n```", color=C_INFO))
        elif cmd in ("curl","wget"):
            cmd_str = f"{cmd} {' '.join(sub)}"
            loader  = await Loader(msg.channel, f"🌐 {cmd}...", cmd_str).start()
            out, err, code = await rodar_async(cmd_str + " 2>&1", 30)
            if code == 0: await loader.ok(cmd, cortar(out or "OK"))
            else:         await loader.erro(f"Erro: {cmd}", cortar(err or out))
        elif cmd == "ping":
            host = sub[0] if sub else "8.8.8.8"
            loader = await Loader(msg.channel, f"ping {host}...", f"ping -c 4 {host}").start()
            out, err, code = await rodar_async(f"ping -c 4 {host} 2>&1", 15)
            if code == 0: await loader.ok(f"ping {host}", cortar(out))
            else:         await loader.erro(f"ping {host}", cortar(err or out))
        elif cmd in ("netstat","ss","ifconfig","ip"):
            out, _, _ = await rodar_async(f"{cmd} {' '.join(sub)} 2>&1", 10)
            await msg.channel.send(embed=discord.Embed(
                title=f"🌐 {cmd}", description=f"```\n{cortar(out)}\n```", color=C_INFO))
        elif cmd in ("nmap","traceroute","dig","nslookup","host"):
            loader = await Loader(msg.channel, f"🌐 {cmd}...",
                                  f"{cmd} {' '.join(sub)}").start()
            out, err, code = await rodar_async(f"{cmd} {' '.join(sub)} 2>&1", 30)
            if code == 0: await loader.ok(cmd, cortar(out))
            else:         await loader.erro(f"Erro: {cmd}", cortar(err or out))
        elif cmd in ("touch","ln","chmod","chown"):
            await msg.channel.send(embed=discord.Embed(
                title=f"✅ {cmd}", description="*(simulado no Discord)*", color=C_OK))
        elif cmd in ("mv","cp"):
            if len(sub) >= 2:
                await msg.channel.send(embed=discord.Embed(
                    title=f"✅ {cmd}",
                    description=f"`{sub[0]}` → `{sub[1]}` *(simulado)*", color=C_OK))
            else:
                await msg.channel.send(embed=discord.Embed(
                    description=f"```bash\n{cmd} <origem> <destino>\n```", color=C_ERRO))
        elif cmd in ("kill","killall"):
            await msg.channel.send(embed=discord.Embed(
                title="✅ kill",
                description=f"Processo `{sub[0] if sub else '?'}` encerrado. *(simulado)*",
                color=C_AVISO))
        elif cmd == "cat" and sub:
            cmd_str = f"cat {' '.join(sub)} 2>&1"
            out, err, code = await rodar_async(cmd_str, 10)
            await msg.channel.send(embed=discord.Embed(
                title=f"📄 cat {sub[0]}",
                description=f"```\n{cortar(out or err)}\n```",
                color=C_OK if code == 0 else C_ERRO))
        elif cmd in ("nano","vim","vi","code"):
            await msg.channel.send(embed=discord.Embed(
                title=f"📝 {cmd}",
                description="Editores interativos não funcionam no Discord.\nUse `cat <arq>` para ler ou `echo 'texto'` para escrever.",
                color=C_AVISO))
        elif cmd == "man" and sub:
            out, _, _ = await rodar_async(f"man {sub[0]} 2>&1 | head -25 | col -bx")
            await msg.channel.send(embed=discord.Embed(
                title=f"📖 man {sub[0]}",
                description=f"```\n{cortar(out or 'Página não encontrada.')}\n```",
                color=C_INFO))
        elif cmd in ("help","--help","-h","fox"):
            await h_help(msg)
        else:
            # Tenta executar no sistema
            loader = await Loader(msg.channel, f"$ {cmd}", full).start()
            out, err, code = await rodar_async(full + " 2>&1", CMD_TIMEOUT)
            output = out or err or "(sem saída)"
            if code == 0: await loader.ok(f"$ {cmd}", cortar(output))
            else:         await loader.erro(f"Erro: $ {cmd}", cortar(output))

    except Exception as ex:
        await msg.channel.send(embed=discord.Embed(
            title="❌ Erro interno",
            description=f"```\n{str(ex)[:400]}\n```", color=C_ERRO))

    await bot.process_commands(msg)

# ══════════════════════════════════════════════════════════════════════════════
#  STATUS ROTATIVO
# ══════════════════════════════════════════════════════════════════════════════
STATUS = [
    (discord.ActivityType.watching,  "o terminal 🦊"),
    (discord.ActivityType.playing,   "pip install tudo"),
    (discord.ActivityType.listening, "git push origin main"),
    (discord.ActivityType.watching,  "help para ajuda"),
    (discord.ActivityType.playing,   "pkg install python"),
]
_si = 0

@tasks.loop(seconds=30)
async def status_loop():
    global _si
    t, n = STATUS[_si % len(STATUS)]
    await bot.change_presence(activity=discord.Activity(type=t, name=n))
    _si += 1

@bot.event
async def on_ready():
    print(f"\n{'═'*50}")
    print(f"  🦊 Fox Terminal Bot — ONLINE")
    print(f"  Usuário : {bot.user}")
    print(f"  Servidores: {len(bot.guilds)}")
    print(f"  Cargo   : {CARGO_ID}")
    print(f"{'═'*50}\n")
    status_loop.start()

# ══════════════════════════════════════════════════════════════════════════════
#  KEEP ALIVE para Render + UptimeRobot
# ══════════════════════════════════════════════════════════════════════════════
from flask import Flask
from threading import Thread

app_flask = Flask("")

@app_flask.route("/")
def home():
    return f"🦊 Fox Terminal Bot — Online | uptime: {uptime()}"

@app_flask.route("/health")
def health():
    return "OK", 200

def run_flask():
    app_flask.run(host="0.0.0.0", port=8080)

def keep_alive():
    Thread(target=run_flask, daemon=True).start()

# ══════════════════════════════════════════════════════════════════════════════
#  INICIAR
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    if not TOKEN:
        print("❌ ERRO: variável DISCORD_TOKEN não definida!")
        print("   No Render: vá em Environment > Add Environment Variable")
        print("   DISCORD_TOKEN = seu_token_aqui")
        sys.exit(1)
    keep_alive()
    print("🚀 Iniciando Fox Terminal Bot...")
    bot.run(TOKEN)
