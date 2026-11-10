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
TODOLIST_API = os.environ.get("TODOLIST_API", "http://127.0.0.1:4860").rstrip("/")
BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "").strip()

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
    if not BOT_TOKEN:
        print("\n=======================================================")
        print("🔑 Token de Bot Discord requis")
        print("=======================================================")
        print("Pour lancer ce bot, obtenez un token sur https://discord.com/developers/applications")
        print("puis lancez :")
        print("    export DISCORD_BOT_TOKEN=\"votre_token_ici\"")
        print("    python3 discord_bot.py\n")
        sys.exit(1)

    bot.run(BOT_TOKEN)
