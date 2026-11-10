#!/usr/bin/env python3
"""
Bot Discord interactif pour ToDoList.
Permet aux membres d'un groupe de projet de consulter, ajouter et terminer des tâches
directement depuis un salon Discord en se synchronisant avec l'application ToDoList.

Utilisation :
    1. Installez discord.py :
       pip install discord.py

    2. Lancez le bot avec votre token Discord :
       export DISCORD_BOT_TOKEN="votre_token_bot"
       python3 discord_bot.py

Commandes Discord disponibles dans votre salon :
    !todo                 -> Affiche la liste des tâches ouvertes du projet
    !todo add <titre>     -> Crée une nouvelle tâche
    !todo done <id>       -> Marque une tâche comme terminée
    !todo folders         -> Affiche les dossiers du projet
    !todo help            -> Affiche ce menu d'aide
"""

import os
import sys
import json
import urllib.request
import urllib.error

# URL de l'API locale ou distante de ToDoList
TODOLIST_API = os.environ.get("TODOLIST_API", "http://127.0.0.1:4848").rstrip("/")

def resolve_bot_token():
    """Récupère et nettoie le token Discord depuis les arguments CLI, l'environnement ou les fichiers."""
    # 1. Argument en ligne de commande (--token <token> ou argument libre)
    if "--token" in sys.argv:
        try:
            idx = sys.argv.index("--token")
            return sys.argv[idx + 1].strip().strip("'\"")
        except (IndexError, ValueError):
            pass
    for arg in sys.argv[1:]:
        if not arg.startswith("-") and len(arg) > 20:
            return arg.strip().strip("'\"")

    # 2. Variable d'environnement
    token = os.environ.get("DISCORD_BOT_TOKEN", "").strip().strip("'\"")
    if token:
        return token

    # 3. Fichier de token local (.discord_token, token.txt)
    for fname in (".discord_token", "token.txt", ".env"):
        if os.path.exists(fname):
            try:
                with open(fname, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("DISCORD_BOT_TOKEN="):
                            return line.split("=", 1)[1].strip().strip("'\"")
                        elif len(line) > 30 and not line.startswith("#"):
                            return line.strip().strip("'\"")
            except Exception:
                pass

    return ""

try:
    import discord
    from discord.ext import commands
except ImportError:
    print("\n❌ La bibliothèque 'discord.py' n'est pas installée.")
    print("👉 Pour installer le bot Discord, exécutez simplement :")
    print("   pip install discord.py\n")
    sys.exit(1)


def api_request(path, method="GET", data=None):
    """Effectue un appel HTTP vers l'API ToDoList."""
    url = f"{TODOLIST_API}{path}"
    headers = {"Content-Type": "application/json", "User-Agent": "ToDoList-DiscordBot/2.0"}
    body = json.dumps(data).encode("utf-8") if data else None

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        return {"error": f"Impossible de contacter ToDoList sur {TODOLIST_API} : {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


@bot.event
async def on_ready():
    print(f"\n=======================================================")
    print(f"🤖 Bot Discord ToDoList connecté : {bot.user} (ID: {bot.user.id})")
    print(f"🔗 Connecté à l'API ToDoList : {TODOLIST_API}")
    print(f"Tapez !todo dans votre salon Discord pour démarrer !")
    print(f"=======================================================\n")
    await bot.change_presence(activity=discord.Game(name="!todo help | ToDoList"))


@bot.group(name="todo", invoke_without_command=True)
async def todo_group(ctx):
    """Affiche les tâches ouvertes par défaut."""
    await todo_list(ctx)


@todo_group.command(name="list")
async def todo_list(ctx):
    """Affiche la liste des tâches actuelles classées par dossier."""
    data = api_request("/api/data")
    if "error" in data:
        await ctx.send(f"❌ {data['error']}\n*Vérifiez que votre application ToDoList est bien lancée.*")
        return

    tasks = data.get("tasks", [])
    folders = {f["id"]: f["name"] for f in data.get("folders", [])}

    open_tasks = [t for t in tasks if not t.get("completed")]

    if not open_tasks:
        embed = discord.Embed(
            title="🎉 Aucune tâche en attente !",
            description="Toutes les tâches du projet sont terminées. Bravo à l'équipe !",
            color=0x10B981
        )
        embed.set_footer(text="ToDoList • Projet d'équipe")
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(
        title=f"📋 Tâches du Projet ({len(open_tasks)} en attente)",
        color=0x5865F2,
        description="Voici la liste des tâches à réaliser pour l'équipe :"
    )

    prio_emojis = {
        "urgent": "🔴",
        "high": "🟠",
        "normal": "🟢",
        "low": "⚪"
    }

    # Grouper par dossier
    grouped = {}
    for t in open_tasks:
        f_name = folders.get(t.get("folder_id"), "Général")
        grouped.setdefault(f_name, []).append(t)

    for f_name, t_list in grouped.items():
        lines = []
        for t in t_list:
            prio = prio_emojis.get(t.get("priority"), "🟢")
            lines.append(f"`#{t['id']}` {prio} **{t['title']}**")
        embed.add_field(name=f"📁 {f_name}", value="\n".join(lines), inline=False)

    embed.set_footer(text="Pour terminer une tâche : !todo done <id> | Pour ajouter : !todo add <titre>")
    await ctx.send(embed=embed)


@todo_group.command(name="add")
async def todo_add(ctx, *, title: str = None):
    """Ajoute une nouvelle tâche au projet."""
    if not title:
        await ctx.send("⚠️ Précisez le titre de la tâche. Exemple : `!todo add Rédiger l'introduction`")
        return

    author_name = ctx.author.display_name
    res = api_request("/api/tasks", method="POST", data={
        "title": title,
        "author": author_name,
        "priority": "normal"
    })

    if "error" in res:
        await ctx.send(f"❌ {res['error']}")
        return

    embed = discord.Embed(
        title="📝 Tâche ajoutée avec succès !",
        description=f"**{res.get('title')}**",
        color=0x3B82F6
    )
    embed.add_field(name="Identifiant", value=f"`#{res.get('id')}`", inline=True)
    embed.add_field(name="Ajoutée par", value=author_name, inline=True)
    embed.set_footer(text="ToDoList • Projet d'équipe")
    await ctx.send(embed=embed)


@todo_group.command(name="done")
async def todo_done(ctx, task_id: int = None):
    """Coche une tâche comme terminée."""
    if task_id is None:
        await ctx.send("⚠️ Précisez le numéro de la tâche. Exemple : `!todo done 4`")
        return

    author_name = ctx.author.display_name
    res = api_request(f"/api/tasks/{task_id}", method="PUT", data={
        "completed": 1,
        "author": author_name
    })

    if not res or "error" in res:
        await ctx.send(f"❌ Tâche #{task_id} introuvable.")
        return

    embed = discord.Embed(
        title="✅ Tâche marquée comme terminée !",
        description=f"~~{res.get('title')}~~",
        color=0x10B981
    )
    embed.add_field(name="Validée par", value=author_name, inline=True)
    embed.set_footer(text="ToDoList • Projet d'équipe")
    await ctx.send(embed=embed)


@todo_group.command(name="folders")
async def todo_folders(ctx):
    """Affiche la liste des dossiers du projet."""
    data = api_request("/api/data")
    if "error" in data:
        await ctx.send(f"❌ {data['error']}")
        return

    folders = data.get("folders", [])
    if not folders:
        await ctx.send("Aucun dossier créé.")
        return

    embed = discord.Embed(title="📁 Dossiers du Projet", color=0x8B5CF6)
    lines = [f"• **{f['name']}** (ID: `{f['id']}`)" for f in folders]
    embed.description = "\n".join(lines)
    embed.set_footer(text="ToDoList • Projet d'équipe")
    await ctx.send(embed=embed)


@todo_group.command(name="help")
async def todo_help(ctx):
    """Affiche l'aide des commandes."""
    embed = discord.Embed(
        title="🎮 Aide ToDoList pour Discord",
        description="Gérez les tâches de votre équipe directement dans Discord :",
        color=0x5865F2
    )
    embed.add_field(name="`!todo` ou `!todo list`", value="Affiche toutes les tâches ouvertes du projet", inline=False)
    embed.add_field(name="`!todo add <titre>`", value="Crée une nouvelle tâche dans le projet", inline=False)
    embed.add_field(name="`!todo done <id>`", value="Marque la tâche #ID comme terminée", inline=False)
    embed.add_field(name="`!todo folders`", value="Affiche les dossiers de votre projet", inline=False)
    embed.set_footer(text="Synchronisé en direct avec votre application ToDoList")
    await ctx.send(embed=embed)


if __name__ == "__main__":
    token = resolve_bot_token()

    # Détection des erreurs courantes de token
    if token.startswith("http://") or token.startswith("https://"):
        print("\n❌ ERREUR : L'URL que vous avez fournie est une URL de Webhook Discord, pas un Token de Bot !")
        print("👉 Les Webhooks Discord s'utilisent directement dans l'application ToDoList (Options > Discord & Webhooks).")
        print("👉 Pour ce Bot, vous devez créer un Bot sur https://discord.com/developers/applications > onglet 'Bot' > 'Reset Token'.\n")
        sys.exit(1)

    if token.isdigit():
        print(f"\n❌ ERREUR : Le token '{token}' semble être un Client ID / Application ID (chiffres uniquement).")
        print("👉 Le Token de Bot est une clé secrète longue (ex: MTA2ND... ou MTI0...).\n")
        print("Obtenez-le sur : https://discord.com/developers/applications > Votre Application > 'Bot' > 'Reset Token'.\n")
        sys.exit(1)

    if not token:
        print("\n=======================================================")
        print("🔑 Token de Bot Discord requis")
        print("=======================================================")
        print("Pour lancer ce bot, obtenez un token sur https://discord.com/developers/applications")
        print("puis lancez :")
        print("    python3 discord_bot.py --token \"votre_token_ici\"")
        print("ou :")
        print("    export DISCORD_BOT_TOKEN=\"votre_token_ici\"")
        print("    python3 discord_bot.py\n")
        
        # Invite interactive si le terminal est interactif
        try:
            val = input("Ou collez votre Token de Bot ici (laissez vide pour quitter) : ").strip().strip("'\"")
            if val:
                token = val
            else:
                sys.exit(1)
        except (KeyboardInterrupt, EOFError):
            sys.exit(1)

    try:
        bot.run(token)
    except discord.errors.LoginFailure:
        print("\n" + "=" * 65)
        print("❌ ERREUR DISCORD : Token de Bot invalide ou refusé (401 Unauthorized)")
        print("=" * 65)
        print("Le token fourni n'a pas été reconnu par les serveurs de Discord.")
        print("\n🔍 Comment obtenir le bon Token de Bot :")
        print("  1. Rendez-vous sur : https://discord.com/developers/applications")
        print("  2. Cliquez sur votre application")
        print("  3. Dans le menu de gauche, cliquez sur l'onglet 'Bot' (PAS 'General Information')")
        print("  4. Sous le nom du bot, cliquez sur 'Reset Token' puis 'Copy'")
        print("  5. Important : Un peu plus bas dans la même page, activez :")
        print("     [x] Message Content Intent (indispensable pour lire !todo)")
        print("  6. Relancez ensuite :")
        print("     python3 discord_bot.py --token \"LE_TOKEN_COPIÉ\"")
        print("=" * 65 + "\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur inattendue du bot Discord : {e}\n")
        sys.exit(1)
