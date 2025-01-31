
import discord
from discord.ext import commands
import asyncio
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from datetime import datetime, timedelta
import uvicorn
from typing import Dict, Optional
import logging
from sqlalchemy import create_engine, Column, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import uuid
from pydantic_settings import BaseSettings
from starlette.status import HTTP_403_FORBIDDEN

class Settings(BaseSettings):
    DISCORD_TOKEN: str
    OWNER_ID: str
    API_KEY: str
    DATABASE_URL: str = "sqlite:///./hidden_messages.db"
    
    class Config:
        env_file = ".env"

settings = Settings()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

Base = declarative_base()

class HiddenMessage(Base):
    __tablename__ = "hidden_messages"
    
    id = Column(String, primary_key=True)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    author_id = Column(String, nullable=False)
    category = Column(String, nullable=True)

engine = create_engine(settings.DATABASE_URL)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

app = FastAPI(title="Discord Hidden Messages API")
api_key_header = APIKeyHeader(name="X-API-Key")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

active_users: Dict[str, datetime] = {}

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header != settings.API_KEY:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
    return api_key_header

class MessageManager:
    def __init__(self):
        self.db = SessionLocal()
    
    def add_message(self, content: str, author_id: str, category: Optional[str] = None) -> str:
        message_id = str(uuid.uuid4())[:8]
        message = HiddenMessage(
            id=message_id,
            content=content,
            author_id=author_id,
            category=category
        )
        try:
            self.db.add(message)
            self.db.commit()
            return message_id
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding message: {e}")
            raise
    
    def get_messages(self, category: Optional[str] = None):
        query = self.db.query(HiddenMessage)
        if category:
            query = query.filter(HiddenMessage.category == category)
        return query.all()
    
    def delete_message(self, message_id: str) -> bool:
        message = self.db.query(HiddenMessage).filter(HiddenMessage.id == message_id).first()
        if message:
            self.db.delete(message)
            self.db.commit()
            return True
        return False

message_manager = MessageManager()

@app.post("/ping/{user_id}")
async def ping(user_id: str, api_key: str = Depends(get_api_key)):
    active_users[user_id] = datetime.utcnow()
    logger.info(f"Received ping from user {user_id}")
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/check/{user_id}")
async def check_user(user_id: str, api_key: str = Depends(get_api_key)):
    if user_id not in active_users:
        return {"active": False}
    
    if datetime.utcnow() - active_users[user_id] > timedelta(seconds=30):
        del active_users[user_id]
        return {"active": False}
    
    return {"active": True}

def check_app_running(user_id: str) -> bool:
    if user_id not in active_users:
        return False
    return datetime.utcnow() - active_users[user_id] <= timedelta(seconds=10)

@bot.event
async def on_ready():
    logger.info(f"Bot is ready {bot.user}")
    await bot.change_presence(activity=discord.Game(name="Watching messages"))

@bot.command(name="viewadd")
async def viewadd(ctx, category: Optional[str] = None, *, message: str):
   
    try:
        await ctx.message.delete()
    except Exception as e:
        logger.error(f"Error deleting message: {e}")

    if str(ctx.author.id) != settings.OWNER_ID:
        await ctx.author.send("You don't have permission to do this command!")
        return

    if not check_app_running(str(ctx.author.id)):
        await ctx.author.send("You need to have the secret active to do this command!")
        return

    try:
        message_id = message_manager.add_message(message, str(ctx.author.id), category)
        await ctx.author.send(
            f"Message was successfully !\n"
            f"ID: `{message_id}`\n"
            f"Category: {category or 'Not set'}"
        )
        logger.info(f"Added new message {message_id} by user {ctx.author.id}")
    except Exception as e:
        logger.error(f"Error in viewadd: {e}")
        await ctx.author.send("There was an error while adding a new message")

@bot.command(name="view")
async def view(ctx, category: Optional[str] = None):

    try:
        await ctx.message.delete()
    except Exception as e:
        logger.error(f"Error deleting message: {e}")

    if not check_app_running(str(ctx.author.id)):
        await ctx.author.send("You need to have secret open to run this command")
        return

    try:
        messages = message_manager.get_messages(category)
        
        if not messages:
            await ctx.author.send("No messages" + 
                                (f" In category {category}" if category else ""))
            return

        content = "**Secret messages**\n\n"
        if category:
            content += f"Category: {category}\n\n"

        for msg in messages:
            content += (
                f"**ID: `{msg.id}`** | {msg.timestamp.strftime('%Y-%m-%d %H:%M')}\n"
                f"{'=' * 40}\n"
                f"{msg.content}\n\n"
            )

        while content:
            if len(content) <= 1900:
                await ctx.author.send(content)
                break
            split_index = content[:1900].rfind('\n')
            await ctx.author.send(content[:split_index])
            content = content[split_index+1:]

        logger.info(f"Sent messages to user {ctx.author.id}")
    except Exception as e:
        logger.error(f"Error in view: {e}")
        await ctx.author.send("There was an error while reading the database")

@bot.command(name="viewdelete")
async def viewdelete(ctx, message_id: str):
   
    try:
        await ctx.message.delete()
    except Exception as e:
        logger.error(f"Error deleting message: {e}")

    if str(ctx.author.id) != settings.OWNER_ID:
        await ctx.author.send("You dont have the permission to do this command!")
        return

    if not check_app_running(str(ctx.author.id)):
        await ctx.author.send("You need to have secret running to do this command!")
        return

    try:
        if message_manager.delete_message(message_id):
            await ctx.author.send(f"Message `{message_id}` was deleted.")
            logger.info(f"Deleted message {message_id} by user {ctx.author.id}")
        else:
            await ctx.author.send(f"Message`{message_id}` not found.")
    except Exception as e:
        logger.error(f"Error in viewdelete: {e}")
        await ctx.author.send("There was an error while reading the message")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.CommandNotFound):
        return
    
    error_message = f"There was an error: {str(error)}"
    logger.error(f"Command error: {error}")
    
    try:
        await ctx.author.send(error_message)
    except:
        try:
            await ctx.send(error_message)
        except:
            pass

async def run_bot():
    try:
        await bot.start(settings.DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")

async def run_api():
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8000, #change this if you want different port
        log_level="info"
    )
    server = uvicorn.Server(config)
    try:
        await server.serve()
    except Exception as e:
        logger.error(f"Error starting API server: {e}")

async def main():
    try:
        await asyncio.gather(run_bot(), run_api())
    except Exception as e:
        logger.error(f"Error in main: {e}")

if __name__ == "__main__":
    asyncio.run(main())
