import base58 
import logging
import sys
import json
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from decimal import Decimal
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler
)
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown

def safe_markdown(text: str) -> str:
    if not text:
        return ""
    special_chars = r'_*[]()~`>#+-=|{}.!'
    result = ""
    for char in str(text):
        if char in special_chars:
            result += f'\\{char}'
        else:
            result += char
    return result
def md(text: str) -> str:
    return safe_markdown(text)
import os
import signal
from solana.rpc.api import Client
from solders.pubkey import Pubkey
import solders
import time
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot_activity.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"
SOLANA_EXPLORER_URL = "https://solscan.io/account/"
ADDRESS, NICKNAME = range(2)
BOT_TOKEN = os.getenv('BOT_TOKEN', '8036121761:AAFKbM3IewRa3_AhOCp-9qHMhZWsbvMEJSE')
print("="*50)
print("🤖 ЗАПУСК БОТА")
print("="*50)
print(f"Токен: {BOT_TOKEN[:15]}...")
TRON_API_KEY = "2eba4560-3d0b-484b-9eaf-7180b4216f28"
headers = {"TRON-PRO-API-KEY": TRON_API_KEY}
TRON_NETWORK = "https://api.trongrid.io"
TRC20_CONTRACTS = {
    'USDT': {
        'address': 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t',
        'decimals': 6,
        'symbol': 'USDT'
    },
    'USDC': {
        'address': 'TEkxiTehnzSmSe2XqrBj4w32RUN966rdz8',
        'decimals': 6,
        'symbol': 'USDC'
    },
    'TUSD': {
        'address': 'TUpMhErZL2fhh4sVNULAbNKLokS4GjC1F4',
        'decimals': 18,
        'symbol': 'TUSD'
    },
    'JUST': {
        'address': 'TCFLL5dx5ZJdKnWuesXxi1VPwjLVmWZZy9',
        'decimals': 18,
        'symbol': 'JUST'
    },
    'BTT': {
        'address': 'TAFjULxiVgT4qWk6UZwjqwZXTSaGaqnVp4',
        'decimals': 18,
        'symbol': 'BTT'
    },
    'WIN': {
        'address': 'TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7',
        'decimals': 6,
        'symbol': 'WIN'
    },
}
SPL_TOKENS = {
    'SOL': {
        'symbol': 'SOL',
        'decimals': 9,
        'mint_address': None  # Native token
    },
    'USDC': {
        'symbol': 'USDC',
        'decimals': 6,
        'mint_address': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
    },
    'USDT': {
        'symbol': 'USDT',
        'decimals': 6,
        'mint_address': 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB'
    },
    'RAY': {
        'symbol': 'RAY',
        'decimals': 6,
        'mint_address': '4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R'
    },
    'SRM': {
        'symbol': 'SRM',
        'decimals': 6,
        'mint_address': 'SRMuApVNdxXokk5GT7XD5cUUgXMBCoAz2LHeuAoKWRt'
    },
}
def validate_solana_address(address: str) -> bool:
    try:
        if len(address) != 44:
            return False
        pubkey = Pubkey.from_string(address)
        return str(pubkey) == address
    except:
        return False
def log_user_action(user_id: int, username: str, action: str, details: str = ""):
    if details and len(details) > 200:
        details = details[:197] + "..."
    log_message = f"👤 USER_ID: {user_id} | USERNAME: @{username} | ACTION: {action}"
    if details:
        log_message += f" | DETAILS: {details}"
    logger.info(log_message)
def log_user_click(user_id: int, username: str, button_data: str):
    logger.info(f"👤 USER_ID: {user_id} | USERNAME: @{username} | BUTTON_CLICK: {button_data}")
def log_command(user_id: int, username: str, command: str, args: str = ""):
    log_msg = f"👤 USER_ID: {user_id} | USERNAME: @{username} | COMMAND: {command}"
    if args:
        log_msg += f" | ARGS: {args}"
    logger.info(log_msg)
def validate_tron_address(address: str) -> bool:
    address = address.strip()
    if not address.startswith('T'):
        return False
    if len(address) != 34:
        return False
    base58_chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    if not all(char in base58_chars for char in address):
        return False
    try:
        decoded = base58.b58decode_check(address)
        return len(decoded) == 21
    except ValueError:
        return False
    except Exception as e:
        logger.warning(f"Ошибка при валидации адреса {address}: {e}")
        return False
def detect_wallet_network(address: str) -> str:
    address = address.strip()
    if address.startswith('T') and len(address) == 34:
        try:
            if validate_tron_address(address):
                return "TRON"
        except:
            pass
    if len(address) == 44:
        try:
            import base58
            decoded = base58.b58decode(address)
            if len(decoded) == 32:  
                return "SOLANA"
        except:
            pass
    if address.startswith('0x') and len(address) == 42:
        return "ETHEREUM"
    return "UNKNOWN"
def get_network_emoji(network: str) -> str:
    emoji_map = {
        "TRON": "🌐",
        "SOLANA": "🔷", 
        "ETHEREUM": "⚫",
        "UNKNOWN": "❓"
    }
    return emoji_map.get(network, "❓")
@dataclass
class WalletBalance:
    symbol: str
    amount: Decimal
    contract_address: Optional[str] = None
    usd_value: Optional[Decimal] = None
    network: str = "TRON"  # Добавляем поле для сети
    mint_address: Optional[str] = None  # Для Solana SPL токенов
    def format_amount(self) -> str:
        try:
            if self.symbol in ['TRX', 'SOL', 'ETH']:
                return f"{self.amount:,.6f}"
            elif self.symbol in ['USDT', 'USDC']:
                return f"{self.amount:,.2f}"
            elif self.amount >= Decimal('1000'):
                return f"{self.amount:,.0f}"
            elif self.amount >= Decimal('100'):
                return f"{self.amount:,.1f}"
            elif self.amount >= Decimal('10'):
                return f"{self.amount:,.2f}"
            elif self.amount >= Decimal('1'):
                return f"{self.amount:,.4f}"
            elif self.amount >= Decimal('0.1'):
                return f"{self.amount:,.5f}"
            else:
                return f"{self.amount:,.6f}"
        except Exception as e:
            logger.error(f"Ошибка форматирования суммы {self.symbol}: {self.amount}, ошибка: {e}")
            return str(self.amount)
@dataclass
class TrackedWallet:
    address: str
    user_id: int
    nickname: str
    network: str = "TRON"  # Добавляем поле для сети (TRON, SOLANA)
    description: Optional[str] = None
    balances: Dict[str, WalletBalance] = field(default_factory=dict)
    total_usd_value: Decimal = Decimal('0')
    last_checked: Optional[datetime] = None
    last_transaction: Optional[str] = None
    last_balance_check: Optional[datetime] = None
class WalletTracker:
    def __init__(self):
        self.tracked_wallets: Dict[str, TrackedWallet] = {}
        self._transactions_cache: Dict[str, List[Dict]] = {}
        self._unknown_tokens_cache: Dict[str, Dict] = {}  # Добавьте эту строку
        self.solana_client = Client(SOLANA_RPC_URL)
        self.load_wallets()
    async def classify_tron_wallet(self, address: str) -> dict:
        try:
            trx_balance = await self.get_trx_balance(address, max_retries=2)
            txs = await self.check_recent_transactions(address, hours=24*30)
            tx_count = len(txs)
            if tx_count == 0:
                if trx_balance > Decimal('0'):
                    return {
                        "type": "cold",
                        "name": "Холодный кошелёк (есть баланс, но нет транзакций)",
                        "confidence": 0.85
                    }
                else:
                    return {
                        "type": "cold",
                        "name": "Новый/пустой кошелёк",
                        "confidence": 0.70
                    }
            unique_senders = set()
            unique_receivers = set()
            usdt_txs = 0
            trx_incoming = Decimal('0')
            trx_outgoing = Decimal('0')
            for tx in txs:
                sender = tx.get('from_address')
                receiver = tx.get('to_address')
                if sender:
                    unique_senders.add(sender)
                if receiver:
                    unique_receivers.add(receiver)
                # Считаем USDT транзакции
                if tx.get('token_symbol') == 'USDT' or 'USDT' in str(tx.get('token_symbol', '')).upper():
                    usdt_txs += 1
                # Суммы TRX
                if tx.get('token_symbol') == 'TRX':
                    if tx.get('direction') == 'INCOMING':
                        trx_incoming += tx.get('token_amount', Decimal('0'))
                    elif tx.get('direction') == 'OUTGOING':
                        trx_outgoing += tx.get('token_amount', Decimal('0'))
            # Определяем общие категории
            total_contacts = len(unique_senders) + len(unique_receivers)
            # Биржевой кошелёк
            if (tx_count > 100 and total_contacts > 50) or usdt_txs > 20:
                return {
                    "type": "exchange",
                    "name": "Возможно биржевой кошелёк",
                    "confidence": min(0.95, 0.7 + min(tx_count/1000, 0.25))
                }
            # Активный (горячий) кошелёк
            if tx_count > 10 or usdt_txs > 3:
                return {
                    "type": "hot",
                    "name": "Активный кошелёк",
                    "confidence": min(0.9, 0.6 + min(tx_count/100, 0.3))
                }
            # Неактивный кошелёк
            if tx_count <= 3:
                return {
                    "type": "cold",
                    "name": "Малоактивный кошелёк",
                    "confidence": 0.75
                }
            # По умолчанию
            wallet_type = "hot" if tx_count > 5 else "cold"
            return {
                "type": wallet_type,
                "name": f"Кошелёк с {tx_count} транзакциями",
                "confidence": 0.65
            }
        except Exception as e:
            logger.error(f"Ошибка классификации кошелька {address}: {e}")
            return {
                "type": "unknown",
                "name": f"Ошибка анализа: {str(e)[:50]}",
                "confidence": 0.0
            }
    async def get_sol_balance(self, address: str) -> Decimal:
        try:
            logger.info(f"🔍 Запрос баланса SOL для {address}")
            pubkey = Pubkey.from_string(address)
            response = self.solana_client.get_balance(pubkey)
            
            if response.value is None:
                logger.warning(f"⚠️ Не удалось получить баланс SOL для {address}")
                return Decimal('0')
            lamports = response.value
            sol_balance = Decimal(str(lamports)) / Decimal('1000000000')
            logger.info(f"💰 SOL баланс для {address}: {lamports} lamports = {sol_balance} SOL")
            return sol_balance
        except Exception as e:
            logger.error(f"❌ Ошибка получения SOL баланса: {e}")
            return Decimal('0')
    async def get_spl_token_balances(self, address: str) -> Dict[str, WalletBalance]:
        try:
            logger.info(f"🔍 Запрос SPL балансов для {address}")
            pubkey = Pubkey.from_string(address)
            response = self.solana_client.get_token_accounts_by_owner(
                pubkey,
                solders.rpc.requests.TokenAccountOpts(program_id=Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"))
            )
            balances = {}
            if response.value:
                for token_account in response.value:
                    account_info = token_account.account.data
                    token_mint = "unknown"
                    token_amount = 0
                    for token_name, token_info in SPL_TOKENS.items():
                        if token_info['mint_address']:
                            pass
                    if token_amount > 0:
                        decimals = next((t['decimals'] for t in SPL_TOKENS.values() 
                                       if t['mint_address'] == token_mint), 6)
                        amount = Decimal(str(token_amount)) / Decimal(f"1e{decimals}")
                        symbol = next((t['symbol'] for t in SPL_TOKENS.values() 
                                     if t['mint_address'] == token_mint), f"TOKEN_{token_mint[:6]}")
                        balances[symbol] = WalletBalance(
                            symbol=symbol,
                            amount=amount,
                            contract_address=token_mint,
                            network="SOLANA",
                            mint_address=token_mint
                        )
            logger.info(f"✅ Найдено {len(balances)} SPL токенов для {address}")
            return balances
        except Exception as e:
            logger.error(f"❌ Ошибка получения SPL балансов: {e}")
            return {}
    async def get_solana_transactions(self, address: str, limit: int = 10) -> List[Dict]:
        try:
            logger.info(f"🔍 Запрос транзакций Solana для {address}")
            pubkey = Pubkey.from_string(address)
            signatures = self.solana_client.get_signatures_for_address(
                pubkey,
                limit=limit
            )
            transactions = []
            if signatures.value:
                for sig_info in signatures.value:
                    sig = sig_info.signature
                    tx_response = self.solana_client.get_transaction(
                        sig,
                        encoding="jsonParsed",
                        max_supported_transaction_version=0
                    )
                    if tx_response.value:
                        tx = tx_response.value
                        parsed_tx = await self._parse_solana_transaction(tx, address)
                        if parsed_tx:
                            transactions.append(parsed_tx)
            logger.info(f"✅ Получено {len(transactions)} транзакций Solana для {address}")
            return transactions
        except Exception as e:
            logger.error(f"❌ Ошибка получения транзакций Solana: {e}")
            return []
    async def _parse_solana_transaction(self, tx: Any, wallet_address: str) -> Optional[Dict]:
        try:
            result = {
                'tx_id': str(tx.transaction.signatures[0]) if tx.transaction.signatures else '',
                'timestamp': tx.block_time * 1000 if tx.block_time else 0,
                'time_str': datetime.fromtimestamp(tx.block_time).strftime("%d.%m.%Y %H:%M:%S") if tx.block_time else "Неизвестно",
                'confirmed': True,
                'network': 'SOLANA',
                'type': 'TRANSFER',
                'direction': 'INCOMING', 
                'amount': Decimal('0'),
                'token_symbol': 'SOL'
            }
            return result
        except Exception as e:
            logger.error(f"Ошибка парсинга Solana транзакции: {e}")
            return None
    def load_wallets(self):
        try:
            if not os.path.exists('wallets.json'):
                logger.info("Файл wallets.json не найден, создаю новый")
                self.save_wallets()
                return
            with open('wallets.json', 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    logger.info("Файл wallets.json пуст")
                    return
                data = json.loads(content)
            logger.info(f"Начинаю загрузку {len(data)} кошельков...")
            loaded_count = 0
            for addr, wallet_data in data.items():
                try:
                    user_id_str = str(wallet_data.get('user_id', '0'))
                    try:
                        user_id = int(user_id_str)
                    except (ValueError, TypeError):
                        logger.warning(f"Некорректный user_id для кошелька {addr}: {user_id_str}")
                        continue
                    last_checked = wallet_data.get('last_checked')
                    last_balance_check = wallet_data.get('last_balance_check')
                    if last_checked:
                        try:
                            last_checked = datetime.fromisoformat(last_checked.replace('Z', '+00:00'))
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Ошибка преобразования даты last_checked для {addr}: {e}")
                            last_checked = None
                    if last_balance_check:
                        try:
                            last_balance_check = datetime.fromisoformat(last_balance_check.replace('Z', '+00:00'))
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Ошибка преобразования даты last_balance_check для {addr}: {e}")
                            last_balance_check = None
                    balances = {}
                    total_usd_value = Decimal('0')
                    if 'balances' in wallet_data:
                        for symbol, balance_data in wallet_data['balances'].items():
                            try:
                                amount_str = balance_data.get('amount', '0')
                                if amount_str is None:
                                    amount_str = '0'
                                amount = Decimal(str(amount_str))
                                usd_value_str = balance_data.get('usd_value')
                                usd_value = None
                                if usd_value_str is not None:
                                    usd_value = Decimal(str(usd_value_str))
                                    total_usd_value += usd_value
                                balances[symbol] = WalletBalance(
                                    symbol=symbol,
                                    amount=amount,
                                    contract_address=balance_data.get('contract_address'),
                                    usd_value=usd_value
                                )
                            except Exception as e:
                                logger.warning(f"Ошибка загрузки баланса {symbol} для {addr}: {e}")
                                continue
                    total_usd_str = wallet_data.get('total_usd_value', '0')
                    if total_usd_str is None:
                        total_usd_str = '0'
                    total_usd_value = Decimal(str(total_usd_str))
                    self.tracked_wallets[addr] = TrackedWallet(
                        address=addr,
                        user_id=user_id,
                        nickname=wallet_data.get('nickname', 'Без названия'),
                        description=wallet_data.get('description'),
                        balances=balances,
                        total_usd_value=total_usd_value,
                        last_checked=last_checked,
                        last_transaction=wallet_data.get('last_transaction'),
                        last_balance_check=last_balance_check
                    )
                    loaded_count += 1
                    logger.info(f"Успешно загружен кошелек {addr} для пользователя {user_id}")
                except KeyError as e:
                    logger.error(f"Отсутствует обязательное поле в кошельке {addr}: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Ошибка загрузки кошелька {addr}: {e}")
                    continue
            logger.info(f"Успешно загружено {loaded_count} кошельков")
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка JSON в файле wallets.json: {e}")
            logger.info("Создаю новый файл wallets.json")
            self.tracked_wallets = {}
            self.save_wallets()
        except FileNotFoundError:
            logger.info("Файл wallets.json не найден, создаю новый")
            self.save_wallets()
        except Exception as e:
            logger.error(f"Критическая ошибка при загрузке кошельков: {e}")
            logger.info("Создаю новый файл wallets.json")
            self.tracked_wallets = {}
            self.save_wallets()
    def add_wallet(self, address: str, user_id: int, nickname: str, 
                description: str = None, network: str = "TRON") -> TrackedWallet:
        wallet = TrackedWallet(
            address=address,
            user_id=user_id,
            nickname=nickname,
            network=network,  
            description=description,
            last_checked=datetime.now(),
            last_balance_check=datetime.now()
        )
        self.tracked_wallets[address] = wallet
        async def set_last_transaction():
            try:
                last_tx = await self.get_last_transaction(address, hours=720)
                if last_tx:
                    wallet.last_transaction = last_tx.get('tx_id')
                    logger.info(f"Найдена последняя транзакция для {address}: {last_tx.get('tx_id')[:12]}")
            except Exception as e:
                logger.error(f"Ошибка при поиске последней транзакции: {e}")
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(set_last_transaction())
        else:
            loop.run_until_complete(set_last_transaction())
        self.save_wallets()
        log_user_action(user_id, "N/A", "ADD_WALLET", f"Address: {address}, Nickname: {nickname}")
        logger.info(f"Добавлен новый кошелек: {address} для пользователя {user_id}")
        return wallet
    def save_wallets(self):
        try:
            data = {}
            for addr, wallet in self.tracked_wallets.items():
                balances_data = {}
                for symbol, balance in wallet.balances.items():
                    balances_data[symbol] = {
                        'amount': str(balance.amount),
                        'contract_address': balance.contract_address,
                        'usd_value': str(balance.usd_value) if balance.usd_value is not None else None
                    }
                data[addr] = {
                    'user_id': wallet.user_id,
                    'nickname': wallet.nickname,
                    'description': wallet.description,
                    'balances': balances_data,
                    'total_usd_value': str(wallet.total_usd_value),
                    'last_checked': wallet.last_checked.isoformat() if wallet.last_checked else None,
                    'last_balance_check': wallet.last_balance_check.isoformat() if wallet.last_balance_check else None,
                    'last_transaction': wallet.last_transaction
                }
            with open('wallets.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"Сохранено {len(data)} кошельков в файл")
        except Exception as e:
            logger.error(f"Ошибка сохранения кошельков: {e}")
            try:
                with open('wallets_backup.json', 'w', encoding='utf-8') as f:
                    json.dump({'error': str(e), 'timestamp': datetime.now().isoformat()}, f)
            except:
                pass
    def remove_wallet(self, address: str):
            if address in self.tracked_wallets:
                user_id = self.tracked_wallets[address].user_id
                del self.tracked_wallets[address]
                self.save_wallets()
                log_user_action(user_id, "N/A", "REMOVE_WALLET", f"Address: {address}")
                return True
            return False
    def get_user_wallets(self, user_id: int) -> List[TrackedWallet]:
        return [w for w in self.tracked_wallets.values() if w.user_id == user_id]
    def update_wallet_description(self, address: str, description: str):
        if address in self.tracked_wallets:
            user_id = self.tracked_wallets[address].user_id
            self.tracked_wallets[address].description = description
            self.save_wallets()
            log_user_action(user_id, "N/A", "UPDATE_DESCRIPTION", f"Address: {address}")
            return True
        return False
    async def get_trx_balance(self, address: str, max_retries: int = 3) -> Decimal:
        for attempt in range(max_retries):
            try:
                url = f"{TRON_NETWORK}/v1/accounts/{address}"
                logger.info(f"🔍 Попытка {attempt + 1}: запрос баланса TRX для {address}")
                logger.info(f"📡 URL: {url}")
                if attempt == 0:  # Только для первой попытки логируем ключ
                    logger.info(f"🔑 Используется API ключ: {TRON_API_KEY[:10]}...")
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                    async with session.get(url, headers=headers) as response:
                        logger.info(f"📊 Статус ответа: {response.status}")
                        if response.status == 200:
                            data = await response.json()
                            logger.info(f"✅ Успешный ответ от TRON API (попытка {attempt + 1})")
                            if data.get('data'):
                                account_data = data['data'][0]
                                balance_sun = account_data.get('balance', 0)
                                balance_trx = Decimal(str(balance_sun)) / Decimal('1000000')
                                logger.info(f"💰 TRX баланс для {address}: {balance_sun} sun = {balance_trx} TRX")
                                return balance_trx
                            else:
                                logger.warning(f"⚠️ Нет данных в ответе для {address}")
                                return Decimal('0')
                        elif response.status == 404:
                            logger.error(f"❌ Адрес {address} не найден в сети TRON")
                            raise ValueError("Адрес не существует")
                        elif response.status == 429:
                            wait_time = (attempt + 1) * 5  # Экспоненциальная задержка: 5, 10, 15 секунд
                            logger.warning(f"⚠️ Превышен лимит запросов к TronGrid API")
                            logger.warning(f"⏱️ Жду {wait_time} секунд перед повторной попыткой...")
                            await asyncio.sleep(wait_time)
                            continue  # Пробуем снова
                        elif response.status >= 500:
                            wait_time = (attempt + 1) * 2  # Меньшая задержка для серверных ошибок
                            logger.error(f"❌ Серверная ошибка {response.status} для {address}")
                            logger.warning(f"⏱️ Жду {wait_time} секунд перед повторной попыткой...")
                            await asyncio.sleep(wait_time)
                            continue  # Пробуем снова
                        else:
                            error_text = await response.text()
                            logger.error(f"❌ API ошибка {response.status} для {address}")
                            logger.error(f"📝 Детали ошибки: {error_text[:200]}")
                            break  # Для других ошибок прерываем попытки
            except asyncio.TimeoutError:
                logger.error(f"⏱️ Таймаут при запросе баланса для {address} (попытка {attempt + 1})")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 3
                    logger.warning(f"⏱️ Жду {wait_time} секунд перед повторной попыткой...")
                    await asyncio.sleep(wait_time)
                    continue
            except ValueError as e:
                logger.error(f"❌ Критическая ошибка: {e}")
                raise e  # Пробрасываем критические ошибки дальше
            except Exception as e:
                logger.error(f"❌ Ошибка получения TRX баланса (попытка {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    logger.warning(f"⏱️ Жду {wait_time} секунд перед повторной попыткой...")
                    await asyncio.sleep(wait_time)
                    continue
        logger.error(f"❌ Все {max_retries} попыток получения баланса для {address} завершились неудачей")
        return Decimal('0')
    async def get_trc20_balances_alternative(self, address: str) -> Dict[str, WalletBalance]:
        try:
            url = f"{TRON_NETWORK}/v1/accounts/{address}"
            logger.info(f"🔍 Альтернативный запрос TRC20 балансов для {address}")
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:  
                    logger.info(f"📊 Статус ответа (альтернативный): {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        if not data.get('data'):
                            return {}
                        account_data = data['data'][0]
                        result = {}
                        if 'trc20' in account_data:
                            trc20_list = account_data['trc20']
                            for token_entry in trc20_list:
                                for contract_address, raw_amount in token_entry.items():
                                    for token_name, token_info in TRC20_CONTRACTS.items():
                                        if contract_address.lower() == token_info['address'].lower():
                                            decimals = token_info['decimals']
                                            amount = Decimal(str(raw_amount)) / Decimal(f"1e{decimals}")
                                            
                                            if amount > Decimal('0'):
                                                result[token_name] = WalletBalance(
                                                    symbol=token_info['symbol'],
                                                    amount=amount,
                                                    contract_address=contract_address
                                                )
                                            break
                        logger.info(f"✅ Альтернативный метод нашел {len(result)} токенов")
                        return result
                    else:
                        logger.error(f"❌ Альтернативный метод: API ошибка {response.status}")
                        return {}
        except Exception as e:
            logger.error(f"❌ Ошибка в альтернативном методе получения балансов: {e}")
            return {}
    async def get_token_info(self, contract_address: str) -> Dict[str, Any]:
        try:
            for token_name, token_info in TRC20_CONTRACTS.items():
                if contract_address.lower() == token_info['address'].lower():
                    logger.info(f"✅ Использую кэшированную информацию о токене: {token_name}")
                    return {
                        'symbol': token_info['symbol'],
                        'decimals': token_info['decimals'],
                        'name': token_name
                    }
            if hasattr(self, '_unknown_tokens_cache'):
                if contract_address in self._unknown_tokens_cache:
                    return self._unknown_tokens_cache[contract_address]
            url = f"{TRON_NETWORK}/v1/contracts/{contract_address}"
            logger.info(f"🔍 Запрос информации о токене: {contract_address}")
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url, headers=headers) as response:
                    logger.info(f"📊 Статус ответа API токена: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        contract_info = data.get('data', [{}])[0]
                        name = contract_info.get('contract_name', '')
                        if not name:
                            name = contract_info.get('name', '')
                        if not name:
                            name = contract_info.get('abi', {}).get('entrys', [{}])[0].get('name', '')
                        symbol = contract_info.get('abi', {}).get('entrys', [{}])[0].get('outputs', [{}])[0].get('name', '')
                        if not name or name == 'Unknown':
                            name = f"Token_{contract_address[:6]}"
                        if not symbol or symbol == 'Unknown':
                            symbol = f"TOKEN_{contract_address[:6]}"
                        decimals = 6  # Значение по умолчанию для TRC20
                        try:
                            abi_entries = contract_info.get('abi', {}).get('entrys', [])
                            for entry in abi_entries:
                                if entry.get('name') == 'decimals':
                                    outputs = entry.get('outputs', [])
                                    if outputs:
                                        decimals = int(outputs[0].get('value', 6))
                                        logger.info(f"📏 Найдены decimals: {decimals}")
                        except Exception as e:
                            logger.warning(f"⚠️ Не удалось получить decimals для {contract_address}: {e}")
                        logger.info(f"✅ Получена информация о токене: {name} ({symbol}), decimals={decimals}")
                        result = {
                            'symbol': symbol,
                            'decimals': decimals,
                            'name': name
                        }
                        if not hasattr(self, '_unknown_tokens_cache'):
                            self._unknown_tokens_cache = {}
                        self._unknown_tokens_cache[contract_address] = result
                        
                        return result
                    elif response.status == 404:
                        # Для токенов с 404 создаем базовую информацию
                        result = {
                            'symbol': f"TOKEN_{contract_address[:6]}",
                            'decimals': 6,  # Предполагаем 6 decimals для TRC20
                            'name': f"Token_{contract_address[:6]}"
                        }
                        # Кэшируем
                        if not hasattr(self, '_unknown_tokens_cache'):
                            self._unknown_tokens_cache = {}
                        self._unknown_tokens_cache[contract_address] = result
                        logger.info(f"⚠️ Токен {contract_address} не найден, использую стандартные параметры")
                        return result
                    else:
                        # Обработка других ошибок API
                        error_text = await response.text()
                        logger.warning(f"⚠️ API ошибка {response.status} для токена {contract_address}: {error_text[:200]}")
                        
                        result = {
                            'symbol': f"TOKEN_{contract_address[:6]}",
                            'decimals': 6,
                            'name': f"Token_{contract_address[:6]}"
                        }
                        # Кэшируем даже при ошибках
                        if not hasattr(self, '_unknown_tokens_cache'):
                            self._unknown_tokens_cache = {}
                        self._unknown_tokens_cache[contract_address] = result
                        return result
        except Exception as e:
            logger.warning(f"⚠️ Ошибка получения информации о токене {contract_address}: {e}")
            result = {
                'symbol': f"TOKEN_{contract_address[:6]}",
                'decimals': 6,
                'name': f"Token_{contract_address[:6]}"
            }            
            if not hasattr(self, '_unknown_tokens_cache'):
                self._unknown_tokens_cache = {}
            self._unknown_tokens_cache[contract_address] = result
            return result
    async def get_all_trc20_balances(self, address: str, max_retries: int = 3) -> Dict[str, WalletBalance]:
        for attempt in range(max_retries):
            try:
                url = f"{TRON_NETWORK}/v1/accounts/{address}"
                logger.info(f"🔍 Попытка {attempt + 1}: запрос TRC20 балансов для {address}")
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
                    async with session.get(url, headers=headers) as response:
                        logger.info(f"📊 Статус ответа: {response.status}")
                        if response.status == 200:
                            data = await response.json()
                            logger.info(f"✅ Успешный ответ от TRON API (TRC20) (попытка {attempt + 1})")
                            if not data.get('data'):
                                logger.warning(f"⚠️ Нет данных в ответе API для адреса {address}")
                                return {}
                            account_data = data['data'][0]
                            result = {}
                            trc20_list = account_data.get('trc20', [])
                            logger.info(f"📊 Найдено {len(trc20_list)} TRC20 записей для адреса {address}")
                            # Выводим первые несколько записей для отладки
                            for i, token_entry in enumerate(trc20_list[:3]):
                                logger.info(f"📝 Запись {i+1}: {token_entry}")
                            token_info_cache = {}
                            for token_entry in trc20_list:
                                for contract_address, raw_amount in token_entry.items():
                                    raw_amount_str = str(raw_amount)
                                    if raw_amount == '0' or raw_amount == 0:
                                        continue
                                    try:
                                        if Decimal(raw_amount_str) == Decimal('0'):
                                            continue
                                    except:
                                        pass
                                    logger.info(f"🔧 Обработка токена: контракт={contract_address}, баланс={raw_amount}")
                                    standard_token_found = False
                                    for token_name, token_info in TRC20_CONTRACTS.items():
                                        if contract_address.lower() == token_info['address'].lower():
                                            decimals = token_info['decimals']
                                            amount = Decimal(raw_amount_str) / Decimal(f"1e{decimals}")
                                            
                                            if amount > Decimal('0'):
                                                result[token_name] = WalletBalance(
                                                    symbol=token_info['symbol'],
                                                    amount=amount,
                                                    contract_address=contract_address
                                                )
                                                logger.info(f"✅ Найден стандартный токен: {token_name} = {amount}")
                                            standard_token_found = True
                                            break
                                    if not standard_token_found:
                                        if contract_address in token_info_cache:
                                            token_data = token_info_cache[contract_address]
                                        else:
                                            token_data = await self.get_token_info(contract_address)
                                            token_info_cache[contract_address] = token_data
                                        try:
                                            decimals = token_data['decimals']
                                            amount = Decimal(raw_amount_str) / Decimal(f"1e{decimals}")
                                            if amount > Decimal('0'):
                                                symbol = token_data['symbol']
                                                if symbol in result:
                                                    symbol = f"{symbol}_{contract_address[-4:]}"
                                                if 'USDT' in symbol.upper():
                                                    logger.info(f"💵 Обнаружен USDT-подобный токен: {symbol}")
                                                    usd_value = amount  
                                                    result[symbol] = WalletBalance(
                                                        symbol=symbol,
                                                        amount=amount,
                                                        contract_address=contract_address,
                                                        usd_value=Decimal(str(usd_value))
                                                    )
                                                else:
                                                    result[symbol] = WalletBalance(
                                                        symbol=symbol,
                                                        amount=amount,
                                                        contract_address=contract_address
                                                    )
                                                logger.info(f"🔍 Найден нестандартный токен: {symbol} = {amount} (decimals: {decimals})")
                                        except Exception as e:
                                            logger.warning(f"⚠️ Ошибка обработки токена {contract_address}: {e}")
                            logger.info(f"✅ Всего обработано {len(result)} токенов для адреса {address}")
                            return result
                        elif response.status == 429:
                            wait_time = (attempt + 1) * 5
                            logger.warning(f"⚠️ Превышен лимит запросов. Жду {wait_time} секунд...")
                            await asyncio.sleep(wait_time)
                            continue
                        elif response.status >= 500:
                            wait_time = (attempt + 1) * 2
                            logger.error(f"❌ Серверная ошибка {response.status}")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            error_text = await response.text()
                            logger.error(f"❌ API ошибка: {response.status} для адреса {address}")
                            logger.error(f"📝 Детали: {error_text[:200]}")
                            if attempt == max_retries - 1:  # Последняя попытка
                                break
                            else:
                                wait_time = (attempt + 1) * 3
                                await asyncio.sleep(wait_time)
                                continue
            except asyncio.TimeoutError:
                logger.error(f"⏱️ Таймаут при запросе TRC20 балансов (попытка {attempt + 1})")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 3
                    logger.warning(f"⏱️ Жду {wait_time} секунд перед повторной попыткой...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    break
            except Exception as e:
                logger.error(f"❌ Ошибка получения TRC20 балансов (попытка {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    logger.warning(f"⏱️ Жду {wait_time} секунд перед повторной попыткой...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    break
        logger.error(f"❌ Все {max_retries} попыток получения TRC20 балансов для {address} завершились неудачей")
        return {}
    async def update_wallet_balances(self, address: str, max_retries: int = 3) -> bool:
        try:
            wallet = self.tracked_wallets.get(address)
            if not wallet:
                return False
            logger.info(f"Обновление балансов для кошелька {address} (сеть: {wallet.network})")
            wallet.balances.clear()
            if wallet.network == "TRON":
                trx_balance = await self.get_trx_balance(address, max_retries)
                if trx_balance > Decimal('0'):
                    wallet.balances['TRX'] = WalletBalance(
                        symbol='TRX',
                        amount=trx_balance,
                        contract_address=None,
                        network="TRON"
                    )
                trc20_balances = await self.get_all_trc20_balances(address, max_retries)
                for token_name, balance in trc20_balances.items():
                    balance.network = "TRON"
                    wallet.balances[token_name] = balance
            elif wallet.network == "SOLANA":
                # Для Solana тоже можно добавить retry логику
                sol_balance = await self.get_sol_balance(address)
                if sol_balance > Decimal('0'):
                    wallet.balances['SOL'] = WalletBalance(
                        symbol='SOL',
                        amount=sol_balance,
                        contract_address=None,
                        network="SOLANA"
                    )
                spl_balances = await self.get_spl_token_balances(address)
                for token_name, balance in spl_balances.items():
                    wallet.balances[token_name] = balance
            wallet.last_balance_check = datetime.now()
            self.save_wallets()
            logger.info(f"Балансы для кошелька {address} обновлены. Найдено токенов: {len(wallet.balances)}")
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления балансов для {address}: {e}")
            return False
    async def check_balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        username = user.username if user.username else "NoUsername"
        log_command(user.id, username, "CHECK_BALANCE")
        user_wallets = tracker.get_user_wallets(update.effective_user.id)
        if not user_wallets:
            await update.message.reply_text("📭 У вас нет отслеживаемых кошельков.")
            return
        await update.message.reply_text("⏳ Проверяю балансы ваших кошельков (с повторными попытками)...")
        updated_count = 0
        failed_count = 0
        for i, wallet in enumerate(user_wallets, 1):
            try:
                await update.message.reply_text(f"🔍 Проверяю кошелек {i}/{len(user_wallets)}: {wallet.nickname}")
                success = await tracker.update_wallet_balances(wallet.address, max_retries=3)
                if success:
                    updated_count += 1
                    logger.info(f"✅ Кошелек {wallet.nickname} успешно обновлен")
                else:
                    failed_count += 1
                    logger.warning(f"⚠️ Не удалось обновить кошелек {wallet.nickname}")            
                if i < len(user_wallets):
                    await asyncio.sleep(2)
            except Exception as e:
                failed_count += 1
                logger.error(f"❌ Ошибка при проверке кошелька {wallet.nickname}: {e}")
                continue
        log_user_action(user.id, username, "BALANCE_CHECK_COMPLETE", 
                        f"Wallets: {len(user_wallets)}, Updated: {updated_count}, Failed: {failed_count}")
        if updated_count > 0:
            await update.message.reply_text(f"✅ Проверено {updated_count} кошельков из {len(user_wallets)}!")
            if failed_count > 0:
                await update.message.reply_text(f"⚠️ Не удалось проверить {failed_count} кошельков")
            await my_wallets_command(update, context)
        else:
            await update.message.reply_text("❌ Не удалось проверить балансы. Попробуйте позже.")
    def get_wallet_balance_summary(self, wallet: TrackedWallet) -> str:
        network_emoji = get_network_emoji(wallet.network)
        network_text = wallet.network
        all_balances = wallet.balances.copy()
        if wallet.network == "TRON":
            if 'TRX' not in all_balances:
                all_balances['TRX'] = WalletBalance(
                    symbol='TRX',
                    amount=Decimal('0'),
                    contract_address=None,
                    network="TRON"
                )
            trx_balance = []
            known_tokens = []
            unknown_tokens = []
            usdt_tokens = []
            for symbol, balance in all_balances.items():
                if symbol == 'TRX':
                    trx_balance.append((symbol, balance))
                elif symbol in TRC20_CONTRACTS:
                    known_tokens.append((symbol, balance))
                elif 'USDT' in symbol.upper() or symbol.startswith('USDT'):
                    usdt_tokens.append((symbol, balance))
                else:
                    unknown_tokens.append((symbol, balance))
            lines = []
            lines.append(f"{network_emoji} *{network_text}*")
            if trx_balance:
                lines.append("\n🌐 *TRX (Native):*")
                for symbol, balance in trx_balance:
                    formatted_amount = balance.format_amount()
                    if balance.amount == Decimal('0'):
                        formatted_amount = "0.000000"
                    lines.append(f"  • {symbol}: {formatted_amount}")
            if usdt_tokens:
                lines.append("\n💵 *USDT Токены:*")
                for symbol, balance in usdt_tokens:
                    formatted_amount = balance.format_amount()
                    usd_value = f" (~${balance.usd_value:,.2f})" if balance.usd_value else ""
                    lines.append(f"  • {symbol}: {formatted_amount}{usd_value}")
            if known_tokens:
                lines.append("\n📊 *Известные токены:*")
                for symbol, balance in known_tokens:
                    formatted_amount = balance.format_amount()
                    if balance.amount == Decimal('0'):
                        if symbol in ['USDT', 'USDC']:
                            formatted_amount = "0.00"
                        else:
                            formatted_amount = "0.000000"
                    lines.append(f"  • {symbol}: {formatted_amount}")
            if unknown_tokens:
                lines.append("\n🔍 *Другие токены:*")
                for symbol, balance in unknown_tokens:
                    if balance.amount > Decimal('0'):
                        if balance.contract_address:
                            short_addr = f"{balance.contract_address[:6]}...{balance.contract_address[-4:]}"
                            lines.append(f"  • {symbol} ({short_addr}): {balance.format_amount()}")
                        else:
                            lines.append(f"  • {symbol}: {balance.format_amount()}")
        elif wallet.network == "SOLANA":
            if 'SOL' not in all_balances:
                all_balances['SOL'] = WalletBalance(
                    symbol='SOL',
                    amount=Decimal('0'),
                    contract_address=None,
                    network="SOLANA"
                )
            sol_balance = []
            known_spl_tokens = []
            unknown_spl_tokens = []
            usdc_tokens = []
            usdt_tokens = []
            for symbol, balance in all_balances.items():
                if symbol == 'SOL':
                    sol_balance.append((symbol, balance))
                elif symbol == 'USDC' or 'USDC' in symbol.upper():
                    usdc_tokens.append((symbol, balance))
                elif symbol == 'USDT' or 'USDT' in symbol.upper():
                    usdt_tokens.append((symbol, balance))
                elif symbol in ['RAY', 'SRM']:  # Известные SPL токены
                    known_spl_tokens.append((symbol, balance))
                else:
                    unknown_spl_tokens.append((symbol, balance))
            lines = []
            lines.append(f"{network_emoji} *{network_text}*")
            if sol_balance:
                lines.append("\n🔷 *SOL (Native):*")
                for symbol, balance in sol_balance:
                    formatted_amount = balance.format_amount()
                    if balance.amount == Decimal('0'):
                        formatted_amount = "0.000000"
                    lines.append(f"  • {symbol}: {formatted_amount}")
            if usdc_tokens:
                lines.append("\n💙 *USDC Токены:*")
                for symbol, balance in usdc_tokens:
                    formatted_amount = balance.format_amount()
                    if balance.amount == Decimal('0'):
                        formatted_amount = "0.00"
                    else:
                        formatted_amount = f"{balance.amount:,.2f}"
                    usd_value = f" (~${balance.usd_value:,.2f})" if balance.usd_value else ""
                    lines.append(f"  • {symbol}: {formatted_amount}{usd_value}")
            if usdt_tokens:
                lines.append("\n💵 *USDT Токены:*")
                for symbol, balance in usdt_tokens:
                    formatted_amount = balance.format_amount()
                    if balance.amount == Decimal('0'):
                        formatted_amount = "0.00"
                    else:
                        formatted_amount = f"{balance.amount:,.2f}"
                    usd_value = f" (~${balance.usd_value:,.2f})" if balance.usd_value else ""
                    lines.append(f"  • {symbol}: {formatted_amount}{usd_value}")
            if known_spl_tokens:
                lines.append("\n💰 *Известные SPL токены:*")
                for symbol, balance in known_spl_tokens:
                    formatted_amount = balance.format_amount()
                    lines.append(f"  • {symbol}: {formatted_amount}")
            if unknown_spl_tokens:
                lines.append("\n🔍 *Другие SPL токены:*")
                for symbol, balance in unknown_spl_tokens:
                    if balance.amount > Decimal('0'):
                        if balance.contract_address:
                            short_addr = f"{balance.contract_address[:6]}...{balance.contract_address[-4:]}"
                            lines.append(f"  • {symbol} ({short_addr}): {balance.format_amount()}")
                        else:
                            lines.append(f"  • {symbol}: {balance.format_amount()}")
        elif wallet.network == "ETHEREUM":
            lines = []
            lines.append(f"{network_emoji} *{network_text}*")
            lines.append("\n⚠️ Поддержка Ethereum в разработке")
        else:
            lines = []
            lines.append(f"{network_emoji} *Неизвестная сеть*")
            lines.append("\n⚠️ Эта сеть пока не поддерживается")
        return "\n".join(lines) if lines else "Нет доступных токенов"
    async def get_last_transaction(self, address: str, hours: int = 720) -> Optional[Dict]:
        try:
            transactions = await self.check_recent_transactions(address, hours=hours)
            if transactions:
                transactions.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
                return transactions[0]
            return None
        except Exception as e:
            logger.error(f"Ошибка получения последней транзакции для {address}: {e}")
            return None
    async def check_recent_transactions(self, address: str, hours: int = 24) -> List[Dict]:
        try:
            cache_keys_to_remove = [key for key in self._transactions_cache.keys() if key.startswith(f"{address}_")]
            for key in cache_keys_to_remove:
                del self._transactions_cache[key]
                logger.info(f"🗑️ Очищен кэш транзакций для ключа: {key}")
            cache_key = f"{address}_{hours}"
            if cache_key in self._transactions_cache:
                cached_txs = self._transactions_cache[cache_key]
                if cached_txs:
                    logger.info(f"📦 Использую кэшированные транзакции для {address[:10]}...")
                    return cached_txs
            url = f"{TRON_NETWORK}/v1/accounts/{address}/transactions"
            from datetime import timezone
            current_time_utc = datetime.now(timezone.utc)
            min_timestamp_ms = int((current_time_utc.timestamp() - hours * 3600) * 1000)
            params = {
                'only_confirmed': 'true',
                'limit': 50,
                'min_timestamp': min_timestamp_ms
            }
            logger.info(f"📡 Запрос транзакций для {address[:10]}... за последние {hours} часов")
            logger.info(f"📊 Параметры запроса: min_timestamp={min_timestamp_ms} (до {current_time_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC)")
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.get(url, params=params, headers=headers) as response:
                    logger.info(f"📊 Статус ответа транзакций: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        transactions = data.get('data', [])
                        if transactions:
                            oldest_tx = min(transactions, key=lambda x: x.get('block_timestamp', 0))
                            newest_tx = max(transactions, key=lambda x: x.get('block_timestamp', 0))
                            oldest_time = datetime.fromtimestamp(oldest_tx.get('block_timestamp', 0)/1000)
                            newest_time = datetime.fromtimestamp(newest_tx.get('block_timestamp', 0)/1000)
                            logger.info(f"📊 Получено {len(transactions)} транзакций для {address[:10]}...")
                            logger.info(f"📅 Диапазон времени транзакций: {oldest_time.strftime('%Y-%m-%d %H:%M:%S')} - {newest_time.strftime('%Y-%m-%d %H:%M:%S')}")
                        else:
                            logger.info(f"📭 Нет транзакций для {address[:10]}... за последние {hours} часов")
                        detailed_txs = []
                        for tx in transactions:
                            try:
                                tx_details = await self._parse_transaction_details(tx, address)
                                if tx_details:
                                    detailed_txs.append(tx_details)
                            except Exception as e:
                                logger.error(f"❌ Ошибка парсинга транзакции {tx.get('txID', '')[:12]}: {e}")
                                continue
                        if detailed_txs:
                            self._transactions_cache[cache_key] = detailed_txs
                            logger.info(f"💾 Сохранено {len(detailed_txs)} транзакций в кэш с ключом {cache_key}")
                        detailed_txs.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
                        logger.info(f"✅ Успешно обработано {len(detailed_txs)} транзакций")
                        return detailed_txs
                    elif response.status == 429:
                        logger.warning(f"⚠️ Превышен лимит запросов для адреса {address[:10]}...")
                        self._transactions_cache[cache_key] = []
                        await asyncio.sleep(15)
                        return []
                    elif response.status == 404:
                        logger.warning(f"⚠️ Адрес {address[:10]}... не найден или нет транзакций")
                        self._transactions_cache[cache_key] = []
                        return []
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ API ошибка {response.status} для {address[:10]}...")
                        logger.error(f"📝 Детали: {error_text[:200]}")
                        self._transactions_cache[cache_key] = []
                        return []
        except asyncio.TimeoutError:
            logger.error(f"⏱️ Таймаут при запросе транзакций для {address[:10]}...")
            cache_key = f"{address}_{hours}"
            self._transactions_cache[cache_key] = []
            return []
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке транзакций: {e}", exc_info=True)
            cache_key = f"{address}_{hours}"
            self._transactions_cache[cache_key] = []
            return []
    async def _parse_transaction_details(self, tx: Dict, wallet_address: str) -> Optional[Dict]:
        try:
            tx_id = tx.get('txID', '')
            raw_data = tx.get('raw_data', {})
            contract_list = raw_data.get('contract', [])
            if not contract_list:
                logger.debug(f"Транзакция {tx_id} без контрактов")
                return None
            contract_data = contract_list[0]
            contract_type = contract_data.get('type', '')
            parameter = contract_data.get('parameter', {}).get('value', {})
            owner_address_hex = parameter.get('owner_address', '')
            to_address_hex = parameter.get('to_address', '') or parameter.get('contract_address', '')
            owner_address = self._to_base58(owner_address_hex) if owner_address_hex else ''
            to_address = self._to_base58(to_address_hex) if to_address_hex else ''
            normalized_wallet = wallet_address.strip()
            is_incoming = to_address and to_address == normalized_wallet
            is_outgoing = owner_address and owner_address == normalized_wallet
            if not (is_incoming or is_outgoing):
                is_incoming = to_address_hex and self._hex_to_base58(to_address_hex) == normalized_wallet
                is_outgoing = owner_address_hex and self._hex_to_base58(owner_address_hex) == normalized_wallet
            if not (is_incoming or is_outgoing):
                logger.debug(f"Транзакция {tx_id} не относится к кошельку {normalized_wallet[:10]}...")
                return None
            timestamp = raw_data.get('timestamp', 0)
            if timestamp == 0:
                timestamp = tx.get('block_timestamp', 0)
            dt = datetime.fromtimestamp(timestamp / 1000)
            result = {
                'tx_id': tx_id,
                'timestamp': timestamp,
                'time_str': dt.strftime("%d.%m.%Y %H:%M:%S"),
                'confirmed': True if tx.get('ret', [{}])[0].get('contractRet') == 'SUCCESS' else False,
                'type': contract_type,
                'direction': 'INCOMING' if is_incoming else 'OUTGOING',
                'from_address': owner_address,
                'to_address': to_address
            }
            if contract_type == 'TransferContract':
                amount = Decimal(str(parameter.get('amount', 0))) / Decimal('1000000')
                result.update({
                    'token_symbol': 'TRX',
                    'token_amount': amount,
                    'amount': amount
                })
                logger.info(f"Найдена TRX транзакция: {amount} TRX")
            elif contract_type == 'TransferAssetContract':
                amount = Decimal(str(parameter.get('amount', 0)))
                asset_name = parameter.get('asset_name', 'TRC10')
                result.update({
                    'token_symbol': asset_name,
                    'token_amount': amount,
                    'amount': amount
                })
                logger.info(f"Найдена TRC10 транзакция: {amount} {asset_name}")
            elif contract_type == 'TriggerSmartContract':
                data_hex = parameter.get('data', '')
                contract_address = self._to_base58(parameter.get('contract_address', ''))
                
                if contract_address.lower() == 'tr7nhqjekqxgtci8q8zy4pl8otszgjlj6t':
                    logger.info(f"💵 Обработка USDT транзакции")
                    logger.debug(f"USDT data_hex: {data_hex[:200]}")
                if not data_hex or data_hex == '0x' or len(data_hex) < 10:
                    logger.warning(f"Пустые данные для контракта {contract_address}")
                    token_info = await self.get_token_info(contract_address)
                    result.update({
                        'token_symbol': token_info.get('symbol', 'UNKNOWN_TOKEN'),
                        'token_amount': Decimal('0'),
                        'contract_address': contract_address,
                        'amount': Decimal('0'),
                        'method': 'no_data'
                    })
                else:
                    token_info = await self._decode_trc20_transfer(data_hex, contract_address)
                    if token_info:
                        result.update({
                            'token_symbol': token_info.get('symbol', 'UNKNOWN'),
                            'token_amount': token_info.get('amount', Decimal('0')),
                            'token_decimals': token_info.get('decimals', 6),
                            'contract_address': contract_address,
                            'amount': token_info.get('amount', Decimal('0')),
                            'method': token_info.get('method', 'unknown')
                        })
                        if token_info.get('method') == 'transferFrom' and token_info.get('from_address'):
                            result['from_address_trc20'] = token_info.get('from_address')
                        logger.info(f"✅ Найдена TRC20 транзакция: {token_info.get('amount')} {token_info.get('symbol')} (метод: {token_info.get('method')})")
                        to_address_trc20 = token_info.get('to_address', '')
                        from_address_trc20 = token_info.get('from_address', '')
                        normalized_wallet = wallet_address.strip()
                        if to_address_trc20 and to_address_trc20 == normalized_wallet:
                            result['direction'] = 'INCOMING'
                            logger.debug(f"TRC20 INCOMING: получатель {to_address_trc20} совпадает с кошельком")
                        elif from_address_trc20 and from_address_trc20 == normalized_wallet:
                            result['direction'] = 'OUTGOING'
                            logger.debug(f"TRC20 OUTGOING: отправитель {from_address_trc20} совпадает с кошельком")
                        else:
                            if is_incoming:
                                result['direction'] = 'INCOMING'
                                logger.debug(f"TRC20 INCOMING: определено по глобальным адресам")
                            elif is_outgoing:
                                result['direction'] = 'OUTGOING'
                                logger.debug(f"TRC20 OUTGOING: определено по глобальным адресам")
                            else:
                                logger.debug(f"Не удалось определить направление TRC20 транзакции")
                    else:
                        token_info = await self.get_token_info(contract_address)
                        result.update({
                            'token_symbol': token_info.get('symbol', 'UNKNOWN_CONTRACT'),
                            'token_amount': Decimal('0'),
                            'contract_address': contract_address,
                            'amount': Decimal('0'),
                            'method': 'decode_failed'
                        })
                        logger.warning(f"Не удалось декодировать контракт: {contract_address}, data_hex: {data_hex[:100]}")
            elif contract_type == 'FreezeBalanceContract':
                result.update({
                    'token_symbol': 'TRX',
                    'token_amount': Decimal(str(parameter.get('frozen_balance', 0))) / Decimal('1000000'),
                    'type': 'FREEZE'
                })
                logger.info(f"Найдена заморозка TRX: {result['token_amount']} TRX")
            elif contract_type == 'UnfreezeBalanceContract':
                result.update({
                    'token_symbol': 'TRX',
                    'token_amount': Decimal('0'),
                    'type': 'UNFREEZE'
                })
                logger.info(f"Найдена разморозка TRX")
            else:
                result.update({
                    'token_symbol': 'UNKNOWN',
                    'token_amount': Decimal('0'),
                    'type': contract_type
                })
                logger.info(f"Найден неизвестный тип контракта: {contract_type}")
            return result
        except Exception as e:
            logger.error(f"Ошибка парсинга деталей транзакции {tx.get('txID', '')[:12]}...: {e}")
            logger.debug(f"Транзакция для дебага: {json.dumps(tx, indent=2)[:500]}")
            return None
    def _get_all_transactions_cache(self):
        return self._transactions_cache
    async def _decode_trc20_transfer(self, data_hex: str, contract_address: str) -> Optional[Dict]:
        try:
            if not data_hex:
                logger.debug("Пустые данные для декодирования TRC20")
                return None
            if data_hex.startswith('0x'):
                data_hex = data_hex[2:]
            if len(data_hex) < 138:  # transfer: 8 (method) + 64 (address + amount)
                logger.debug(f"Недостаточно данных для декодирования TRC20: {data_hex}")
                return None
            data_hex = data_hex.lower()
            method_id = data_hex[:8]
            logger.info(f"🔍 Декодирование TRC20: контракт={contract_address}, method={method_id}, data={data_hex[:100]}...")
            token_info = await self.get_token_info(contract_address)
            decimals = token_info.get('decimals', 6)
            symbol = token_info.get('symbol', f"TOKEN_{contract_address[:6]}")
            if method_id == 'a9059cbb':  # transfer
                logger.debug(f"Найден метод transfer для {symbol}")
                if len(data_hex) < 72:
                    logger.warning(f"Недостаточно данных для адреса в transfer: {len(data_hex)} символов")
                    return None
                to_address_hex = data_hex[8:72]
                to_address_hex = to_address_hex.lstrip('0')
                if len(to_address_hex) < 40:
                    to_address_hex = '0' * (40 - len(to_address_hex)) + to_address_hex
                elif len(to_address_hex) > 40:
                    to_address_hex = to_address_hex[-40:]
                if len(data_hex) < 136:
                    logger.warning(f"Недостаточно данных для суммы в transfer: {len(data_hex)} символов")
                    return None
                amount_hex = data_hex[72:136]
                if not amount_hex or all(c == '0' for c in amount_hex):
                    logger.warning(f"Пустая сумма в транзакции: {amount_hex}")
                    return None
                try:
                    raw_amount = int(amount_hex, 16)
                except ValueError as e:
                    logger.warning(f"Неверный hex для суммы {amount_hex}: {e}")
                    return None
                amount = Decimal(str(raw_amount)) / Decimal(f"1e{decimals}")
                to_address = self._hex_to_base58(to_address_hex)
                logger.info(f"✅ Успешно декодирован transfer: {amount} {symbol} → {to_address}")
                return {
                    'symbol': symbol,
                    'amount': amount,
                    'decimals': decimals,
                    'to_address': to_address,
                    'method': 'transfer'
                }
            elif method_id == '23b872dd': 
                logger.debug(f"Найден метод transferFrom для {symbol}")
                if len(data_hex) < 202:
                    logger.warning(f"Недостаточно данных для transferFrom: {len(data_hex)} символов")
                    return None
                from_address_hex = data_hex[8:72]
                from_address_hex = from_address_hex.lstrip('0')
                if len(from_address_hex) < 40:
                    from_address_hex = '0' * (40 - len(from_address_hex)) + from_address_hex
                elif len(from_address_hex) > 40:
                    from_address_hex = from_address_hex[-40:]
                to_address_hex = data_hex[72:136]
                to_address_hex = to_address_hex.lstrip('0')
                if len(to_address_hex) < 40:
                    to_address_hex = '0' * (40 - len(to_address_hex)) + to_address_hex
                elif len(to_address_hex) > 40:
                    to_address_hex = to_address_hex[-40:]
                amount_hex = data_hex[136:200]
                if not amount_hex or all(c == '0' for c in amount_hex):
                    logger.warning(f"Пустая сумма в transferFrom: {amount_hex}")
                    return None
                try:
                    raw_amount = int(amount_hex, 16)
                except ValueError as e:
                    logger.warning(f"Неверный hex для суммы {amount_hex}: {e}")
                    return None
                amount = Decimal(str(raw_amount)) / Decimal(f"1e{decimals}")
                to_address = self._hex_to_base58(to_address_hex)
                from_address = self._hex_to_base58(from_address_hex)
                logger.info(f"✅ Успешно декодирован transferFrom: {from_address} → {to_address}, {amount} {symbol}")
                return {
                    'symbol': symbol,
                    'amount': amount,
                    'decimals': decimals,
                    'from_address': from_address,
                    'to_address': to_address,
                    'method': 'transferFrom'
                }
            else:
                logger.info(f"Неизвестный метод TRC20: {method_id} для контракта {contract_address}")
                known_methods = {
                    '095ea7b3': 'approve',
                    '70a08231': 'balanceOf',
                    'dd62ed3e': 'allowance',
                    '18160ddd': 'totalSupply',
                    '06fdde03': 'name',
                    '95d89b41': 'symbol',
                    '313ce567': 'decimals'
                }
                if method_id in known_methods:
                    logger.info(f"Известный метод {known_methods[method_id]}, но не относящийся к переводу")
                return {
                    'symbol': symbol,
                    'amount': Decimal('0'),
                    'decimals': decimals,
                    'method': 'unknown',
                    'method_id': method_id
                }
        except Exception as e:
            logger.error(f"❌ Критическая ошибка декодирования TRC20 данных: {e}")
            logger.debug(f"Данные для дебага: contract={contract_address}, data_hex={data_hex[:200]}")
            import traceback
            logger.debug(f"Трассировка: {traceback.format_exc()}")
            return None
    def _to_base58(self, hex_address: str) -> str:
        try:
            if hex_address.startswith('T'):
                return hex_address
            if not hex_address.startswith('41') and len(hex_address) == 42:
                pass
            elif len(hex_address) == 40:
                hex_address = '41' + hex_address
            elif len(hex_address) == 66 and hex_address.startswith('0x'):
                hex_address = '41' + hex_address[2:]
            elif len(hex_address) == 64:
                hex_address = '41' + hex_address[:40]
            bytes_address = bytes.fromhex(hex_address)
            base58_address = base58.b58encode_check(bytes_address).decode()
            return base58_address
        except Exception as e:
            logger.error(f"Ошибка преобразования hex в base58: {hex_address}, ошибка: {e}")
            return hex_address 
    def _hex_to_base58(self, hex_str: str) -> str:
        try:
            if not hex_str:
                return ""
            if hex_str.startswith('0x'):
                hex_str = hex_str[2:]
            if len(hex_str) == 40:
                hex_str = '41' + hex_str
            elif len(hex_str) == 42 and hex_str.startswith('41'):
                pass
            elif len(hex_str) > 42:
                logger.debug(f"Слишком длинный hex: {len(hex_str)} символов, обрезаю")
                hex_str = hex_str[-42:]  # Берем последние 42 символа
            elif len(hex_str) < 40:
                logger.debug(f"Слишком короткий hex: {len(hex_str)} символов, дополняю")
                hex_str = '0' * (40 - len(hex_str)) + hex_str
                hex_str = '41' + hex_str
            bytes_addr = bytes.fromhex(hex_str)
            base58_addr = base58.b58encode_check(bytes_addr).decode()
            return base58_addr
        except ValueError as e:
            logger.warning(f"Ошибка преобразования hex в base58: {hex_str} - {e}")
            return f"INVALID_HEX:{hex_str[:20]}..."
        except Exception as e:
            logger.error(f"Неизвестная ошибка в _hex_to_base58: {e}")
            return "ERROR"
    async def debug_wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        await update.message.reply_text("🔍 Запускаю детальную проверку кошельков...")
        user_wallets = tracker.get_user_wallets(user.id)
        for wallet in user_wallets:
            await update.message.reply_text(f"🔍 Проверяю {wallet.nickname} ({wallet.address[:10]}...)")
            url = f"{TRON_NETWORK}/v1/accounts/{wallet.address}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('data'):
                            account_data = data['data'][0]
                            trc20_list = account_data.get('trc20', [])
                            await update.message.reply_text(
                                f"📊 Найдено {len(trc20_list)} TRC20 записей\n"
                                f"Содержимое: {json.dumps(trc20_list[:3], indent=2)[:1000]}..."
                            )
async def debug_transaction(self, tx_id: str) -> Dict:
    try:
        url = f"{TRON_NETWORK}/v1/transactions/{tx_id}"
        logger.info(f"🔍 Запрос деталей транзакции {tx_id}")
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    logger.error(f"Ошибка API: {response.status}")
                    return {}
    except Exception as e:
        logger.error(f"Ошибка запроса транзакции {tx_id}: {e}")
        return {}
async def debug_tx_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование: /debug_tx <tx_id>")
        return
    tx_id = context.args[0]
    await update.message.reply_text(f"🔍 Анализирую транзакцию {tx_id}...")
    tx_data = await tracker.debug_transaction(tx_id)
    if not tx_data:
        await update.message.reply_text("❌ Не удалось получить данные транзакции")
        return
    response = f"📊 *Детали транзакции:* `{tx_id}`\n\n"
    if 'raw_data' in tx_data:
        raw_data = tx_data['raw_data']
        response += f"*Контракты:* {len(raw_data.get('contract', []))}\n"
        response += f"*Время:* {datetime.fromtimestamp(raw_data.get('timestamp', 0)/1000).strftime('%d.%m.%Y %H:%M:%S')}\n\n"
        for i, contract in enumerate(raw_data.get('contract', [])):
            response += f"*Контракт {i+1}:*\n"
            response += f"Тип: `{contract.get('type', 'Unknown')}`\n"
            param = contract.get('parameter', {}).get('value', {})
            for key, value in param.items():
                if isinstance(value, (str, int, float, bool)):
                    response += f"{key}: `{value}`\n"
                elif key == 'data':
                    response += f"{key}: `{value[:100]}...`\n"
            response += "\n"
    if 'ret' in tx_data:
        ret = tx_data['ret'][0] if tx_data['ret'] else {}
        response += f"*Статус:* {ret.get('contractRet', 'Unknown')}\n"
    await update.message.reply_text(
        response,
        parse_mode=ParseMode.MARKDOWN
    )
class TransactionMonitor:
    def __init__(self, application: Application, tracker: WalletTracker, 
                 check_interval: int = 600): 
        self.application = application
        self.tracker = tracker
        self.check_interval = check_interval  
        self.last_checked: Dict[str, datetime] = {}
        self.running = False
        self.job = None
    async def start(self):
        if self.running:
            return
        self.running = True
        logger.info(f"🚀 Запуск мониторинга транзакций с интервалом {self.check_interval} секунд")
        self.job = self.application.job_queue.run_repeating(
            self.check_all_transactions,
            interval=self.check_interval,
            first=10 
        )
    async def stop(self):
        if self.job:
            self.job.schedule_removal()
        self.running = False
        logger.info("🛑 Мониторинг транзакций остановлен")
    async def send_status_report(self, wallet: TrackedWallet) -> bool:
        try:
            await self.tracker.update_wallet_balances(wallet.address)
            balance_summary = self.tracker.get_wallet_balance_summary(wallet)
            tronscan_link = f"https://tronscan.org/#/address/{wallet.address}"
            current_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            
            notification_text = (
                f"🔔 *Обнаружена новая транзакция*\n\n"
                f"*Кошелек:* `{wallet.address}`\n"
                f"*Название:* {wallet.nickname}\n"
                f"*Время проверки:* {current_time}\n\n"
                f"*Текущие балансы:*\n{balance_summary}\n\n"
                f"[Посмотреть кошелек в TronScan]({tronscan_link})"
            )
            await self.application.bot.send_message(
                chat_id=wallet.user_id,
                text=notification_text,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            logger.info(f"🔔 Отправлено уведомление о транзакции для кошелька {wallet.nickname} ({wallet.address[:8]}...)")
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления для {wallet.address}: {e}")
            return False
    async def check_all_transactions(self, context: ContextTypes.DEFAULT_TYPE):
        if not self.tracker.tracked_wallets:
            logger.info("📭 Нет отслеживаемых кошельков для проверки")
            return
        total_wallets = len(self.tracker.tracked_wallets)
        logger.info(f"🔍 Начинаю проверку транзакций для {total_wallets} кошельков")
        checked_count = 0
        sent_notifications = 0
        errors = 0
        self.tracker._transactions_cache.clear()
        for i, (address, wallet) in enumerate(list(self.tracker.tracked_wallets.items())):
            try:
                logger.info(f"📝 Проверяю кошелек {i+1}/{total_wallets}: {wallet.nickname} ({address[:8]}...)")
                transactions = await self.tracker.check_recent_transactions(address, hours=48)
                if transactions:
                    transactions.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
                    latest_tx = transactions[0]
                    latest_tx_id = latest_tx.get('tx_id')
                    if wallet.last_transaction != latest_tx_id:
                        logger.info(f"📤 Найдена новая транзакция для {wallet.nickname}")
                        logger.info(f"   TXID: {latest_tx_id[:12]}...")
                        wallet.last_transaction = latest_tx_id
                        wallet.last_checked = datetime.now()
                        self.tracker.save_wallets()
                        sent = await self.send_status_report(wallet)
                        if sent:
                            sent_notifications += 1
                        await self.send_transaction_notification(wallet, latest_tx)
                        wallet.last_transaction = latest_tx_id
                        wallet.last_checked = datetime.now()
                        self.tracker.save_wallets() 
                        sent_notifications += 1
                        found_count = len(transactions)
                        logger.info(f"✅ Отправлено уведомление. Найдено транзакций: {found_count}")
                    else:
                        logger.info(f"📭 Для кошелька {wallet.nickname} нет новых транзакций")
                        await self.send_transaction_notification(wallet, latest_tx)
                else:
                    logger.info(f"📭 Для кошелька {wallet.nickname} транзакций не найдено за 48 часов")
                checked_count += 1
                await asyncio.sleep(1) 
            except Exception as e:
                errors += 1
                logger.error(f"❌ Ошибка при проверке транзакций для {address}: {e}", exc_info=True)
                continue
        logger.info(f"✅ Проверка завершена: {checked_count}/{total_wallets} кошельков, "
                    f"отправлено уведомлений: {sent_notifications}, ошибок: {errors}")
    async def send_transaction_notification(self, wallet: TrackedWallet, transaction: Dict):
        try:
            await self.tracker.update_wallet_balances(wallet.address)
            message = self.format_transaction_message(transaction, wallet)
            balance_summary = self.tracker.get_wallet_balance_summary(wallet)
            current_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            notification_text = (
                f"{message}\n"
                f"\n<b>💰 Текущие балансы после транзакции:</b>\n"
                f"{balance_summary}\n"
                f"<b>⏰ Проверено:</b> {current_time}"
            )
            await self.application.bot.send_message(
                chat_id=wallet.user_id,
                text=notification_text,
                parse_mode=ParseMode.HTML,  # Изменено с MARKDOWN на HTML
                disable_web_page_preview=True
            )
            logger.info(f"📤 Отправлено уведомление пользователю {wallet.user_id} о транзакции {transaction['tx_id'][:10]}...")
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления: {e}")
    def format_transaction_message(self, transaction: Dict, wallet: TrackedWallet) -> str:
        tx_id = transaction.get('tx_id', '')
        time_str = transaction.get('time_str', 'Неизвестно')
        direction = transaction.get('direction', '')
        token_symbol = transaction.get('token_symbol', '')
        token_amount = transaction.get('token_amount', Decimal('0'))
        confirmed = transaction.get('confirmed', False)
        transaction_type = transaction.get('type', '')
        if transaction_type == 'FREEZE':
            title_emoji = "❄️"
            title_text = "Заморожены средства"
        elif transaction_type == 'UNFREEZE':
            title_emoji = "☀️"
            title_text = "Разморожены средства"
        elif direction == 'INCOMING':
            title_emoji = "⬇️"
            title_text = "Получены средства"
        else:
            title_emoji = "⬆️"
            title_text = "Отправлены средства"
        if token_amount:
            if token_symbol in ['USDT', 'USDC']:
                amount_str = f"{token_amount:,.2f}"
            elif token_symbol == 'TRX':
                amount_str = f"{token_amount:,.6f}"
            elif token_amount >= Decimal('1000'):
                amount_str = f"{token_amount:,.0f}"
            elif token_amount >= Decimal('100'):
                amount_str = f"{token_amount:,.1f}"
            elif token_amount >= Decimal('0.000001'):
                amount_str = f"{token_amount:,.6f}"
            else:
                amount_str = f"{token_amount}"
        else:
            amount_str = "0"
        if " " in time_str:
            parts = time_str.split(" ")
            if len(parts) >= 2:
                date_part = parts[0]  # Дата
                time_part = parts[1]  # Время
                time_str_formatted = f"⏰ Время: {time_part} дата {date_part}"
            else:
                time_str_formatted = f"⏰ Время: {time_str}"
        else:
            time_str_formatted = f"⏰ Время: {time_str}"
        def escape_html(text):
            if not text:
                return ""
            return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        wallet_name = escape_html(wallet.description or wallet.nickname)
        wallet_address = escape_html(wallet.address)
        title_text = escape_html(title_text)
        amount_str = escape_html(amount_str)
        token_symbol = escape_html(token_symbol)
        time_str_formatted = escape_html(time_str_formatted)
        transaction_type = escape_html(transaction_type)
        tx_id_short = escape_html(f"{tx_id[:12]}...{tx_id[-6:]}") if tx_id else ""
        tronscan_link = f"https://tronscan.org/#/address/{wallet.address}"
        return (
            f"<b>{title_emoji} {title_text}</b>\n"
            f"{time_str_formatted}\n"
            f"<b>🏷️ Кошелек:</b> {wallet_name}\n"
            f"<b>📍 Адрес:</b> <code>{wallet_address}</code>\n\n"
            f"<b>💸 Сумма:</b> {amount_str} {token_symbol}\n"
            f"<b>📊 Тип:</b> {transaction_type}\n"
            f"<b>✅ Статус:</b> {'Подтверждено' if confirmed else 'В обработке'}\n\n"
            f"<b>🔗</b> <a href='{tronscan_link}'>Посмотреть в TronScan</a>\n"
            f"<b>📝 TXID:</b> <code>{tx_id_short}</code>"
        )
tracker = WalletTracker()
async def force_update_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text("🔄 Принудительное обновление всех балансов...")
    user_wallets = tracker.get_user_wallets(user.id)
    for wallet in user_wallets:
        wallet.balances.clear()
        success = await tracker.update_wallet_balances(wallet.address)
        if success:
            await update.message.reply_text(f"✅ {wallet.nickname} обновлен")
        else:
            await update.message.reply_text(f"❌ {wallet.nickname} ошибка")
        await asyncio.sleep(3)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username if user.username else "NoUsername"
    log_command(user.id, username, "START")
    welcome_text = f"""
👋 Привет, {user.first_name}!
Я бот для отслеживания балансов и транзакций TRC20 кошельков.
📋 ДОСТУПНЫЕ КОМАНДЫ:
/add_wallet - Добавить кошелек для отслеживания
/my_wallets - Мои отслеживаемые кошельки с балансами
/check_balance - Проверить балансы кошельков
/remove_wallet - Удалить кошелек из отслеживания
/check_now - Проверить последние транзакции
/last_tx <адрес> - Последняя транзакция кошелька
/settings - Настройки уведомлений
/edit_description - Изменить описание кошелька

💡 КАК ИСПОЛЬЗОВАТЬ:
1. Добавьте TRON кошелек командой /add_wallet
2. Укажите название для кошелька
3. Проверьте баланс командой /check_balance
4. Следите за транзакциями автоматически

📊 ПОДДЕРЖИВАЕМЫЕ ТОКЕНЫ:
• TRX (нативный токен)
• USDT, USDC, TUSD (стабильные монеты)
• JUST, BTT, WIN и другие TRC20 токены
"""

    await update.message.reply_text(welcome_text)
async def add_wallet_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username if user.username else "NoUsername"
    log_user_action(user.id, username, "START_ADD_WALLET")
    await update.message.reply_text(
        "📝 Отправьте адрес кошелька для добавления:\n\n"
        "🌐 Поддерживаемые сети:\n"
        "• TRON (адреса начинаются с 'T', 34 символа)\n"
        "• Solana (44 символа)\n\n"
        "📋 Примеры:\n"
        "• TRON: `Txxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`\n"
        "• Solana: `8xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`\n\n"
        "Бот автоматически определит сеть.\n"
        "Отправьте /cancel для отмены.",
        parse_mode=ParseMode.MARKDOWN
    )
    return ADDRESS
async def add_wallet_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username if user.username else "NoUsername"
    address = update.message.text.strip()
    log_user_action(user.id, username, "ENTER_ADDRESS", f"Address: {address}")    
    network = detect_wallet_network(address)
    network_emoji = get_network_emoji(network)
    if network == "UNKNOWN":
        await update.message.reply_text(
            "❌ Не удалось определить сеть кошелька!\n\n"
            "Проверьте правильность адреса:\n"
            "• TRON: начинается с 'T', 34 символа\n"
            "• Solana: 44 символа\n\n"
            "Попробуйте еще раз:"
        )
        return ADDRESS    
    user_wallets = tracker.get_user_wallets(update.effective_user.id)
    if any(w.address == address for w in user_wallets):
        await update.message.reply_text("❌ Этот кошелек уже отслеживается! Введите другой адрес:")
        return ADDRESS    
    network_names = {
        "TRON": "TRON (TRC20)",
        "SOLANA": "Solana (SPL)",
        "ETHEREUM": "Ethereum (ERC20)"
    }
    network_name = network_names.get(network, network)
    await update.message.reply_text(
        f"{network_emoji} *Определена сеть: {network_name}*\n"
        f"📍 Адрес: `{address}`\n\n"
        "✅ Адрес принят!\n\n"
        "📝 Теперь введите название для этого кошелька:",
        parse_mode=ParseMode.MARKDOWN
    )    
    context.user_data['address'] = address
    context.user_data['network'] = network
    return NICKNAME
async def last_transaction_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username if user.username else "NoUsername"
    if not context.args:
        log_command(user.id, username, "LAST_TX", "NO_ARGS")
        await update.message.reply_text("Укажите адрес кошелька: /last_tx <адрес>")
        return
    address = context.args[0]
    log_command(user.id, username, "LAST_TX", f"Address: {address}")
    user_wallets = tracker.get_user_wallets(update.effective_user.id)
    if not any(w.address == address for w in user_wallets):
        await update.message.reply_text("❌ Этот кошелек не найден среди ваших отслеживаемых кошельков!")
        return
    await update.message.reply_text("🔍 Ищу последнюю транзакцию...")
    last_tx = await tracker.get_last_transaction(address, hours=720)
    if last_tx:
        direction_emoji = "⬇️" if last_tx.get('direction') == 'INCOMING' else "⬆️"
        token_symbol = last_tx.get('token_symbol', 'UNKNOWN')
        token_amount = last_tx.get('token_amount', Decimal('0'))
        time_str = last_tx.get('time_str', '')
        if token_symbol in ['USDT', 'USDC']:
            amount_str = f"{token_amount:,.2f}"
        elif token_symbol == 'TRX':
            amount_str = f"{token_amount:,.6f}"
        else:
            amount_str = f"{token_amount:,.4f}"
        direction_text = "Получено" if last_tx.get('direction') == 'INCOMING' else "Отправлено"
        confirmed = "✅" if last_tx.get('confirmed', False) else "⏳"
        tx_id = last_tx.get('tx_id', '')
        wallet = tracker.tracked_wallets.get(address)
        nickname = wallet.nickname if wallet else "Неизвестный"
        message = (
            f"📊 *Последняя транзакция кошелька:* {nickname}\n"
            f"📍 *Адрес:* `{md(address)}`\n\n"
            f"{direction_emoji} {confirmed} *{time_str}*\n"
            f"*{direction_text}:* {amount_str} {token_symbol}\n\n"
        )
        if tx_id:
            message += f"📝 *TXID:* `{tx_id[:12]}...{tx_id[-6:]}`\n"
            message += f"🔗 [Посмотреть в Tronscan](https://tronscan.org/#/transaction/{md(tx_id)})"
        await update.message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
    else:
        await update.message.reply_text(
            f"📭 Транзакции не найдены за последние 30 дней.\n"
            f"🔗 [Проверить в TronScan](https://tronscan.org/#/address/{address})",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
async def add_wallet_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username if user.username else "NoUsername"
    nickname = update.message.text.strip()
    address = context.user_data.get('address')
    network = context.user_data.get('network', 'TRON')
    network_emoji = get_network_emoji(network)
    clean_nickname = nickname
    if 'http' in nickname.lower() or 'www.' in nickname.lower():
        clean_nickname = nickname.replace('*', '').replace('_', '').replace('`', '')
        clean_nickname = clean_nickname.replace('[', '').replace(']', '').replace('(', '').replace(')', '')
    log_user_action(
        user.id, username, "ENTER_NICKNAME",
        f"Address: {address}, Nickname: {clean_nickname}, Network: {network}"
    )
    if not address:
        await update.message.reply_text(
            "❌ Ошибка: адрес не найден. Начните заново командой /add_wallet"
        )
        return ConversationHandler.END
    if len(clean_nickname) < 2:
        await update.message.reply_text(
            "❌ Название слишком короткое. Введите минимум 2 символа:"
        )
        return NICKNAME
    if len(clean_nickname) > 50:
        await update.message.reply_text(
            "❌ Название слишком длинное. Максимум 50 символов:"
        )
        return NICKNAME
    safe_nickname = safe_markdown(clean_nickname)
    await update.message.reply_text(
        f"⏳ Добавляю кошелек...\n\n"
        f"{network_emoji} *Сеть:* {network}\n"
        f"🏷️ *Название:* {safe_nickname}\n"
        f"📍 *Адрес:* `{address[:10]}...{address[-6:]}`",
        parse_mode=ParseMode.MARKDOWN
    )
    wallet = tracker.add_wallet(
        address=address,
        user_id=user.id,
        nickname=clean_nickname,  # Используем clean_nickname вместо nickname
        description=None,
        network=network
    )
    await update.message.reply_text("⏳ Проверяю баланс нового кошелька...")
    success = await tracker.update_wallet_balances(address)
    wallet = tracker.tracked_wallets.get(address)
    if not success or not wallet:
        await update.message.reply_text(
            "⚠️ Кошелек добавлен, но не удалось проверить баланс.\n"
            "Попробуйте позже командой /check_balance"
        )
    else:
        balance_summary = tracker.get_wallet_balance_summary(wallet)
        network_names = {
            "TRON": "TRON 🌐",
            "SOLANA": "Solana 🔷",
            "ETHEREUM": "Ethereum ⚫"
        }
        response = (
            f"✅ *Кошелек успешно добавлен\\!*\n\n"
            f"{network_emoji} *Сеть:* {network_names.get(network, network)}\n"
            f"🏷️ *Название:* {safe_markdown(clean_nickname)}\n"
            f"📍 *Адрес:* `{safe_markdown(address)}`\n\n"
            f"💰 *Балансы:*\n{balance_summary}"
        )
        if network == "TRON":
            wallet_type = await tracker.classify_tron_wallet(address)
            type_labels = {
                "exchange": "🏦 Вероятно биржа",
                "hot": "🔥 Вероятно горячий кошелёк",
                "cold": "❄️ Вероятно холодный кошелёк",
                "unknown": "❓ Тип не определён"
            }
            wallet_type_name = safe_markdown(wallet_type['name'])
            wallet_type_label = type_labels.get(wallet_type['type'], '❓')
            response += (
                f"\n\n🧠 *Тип кошелька:*\n"
                f"{wallet_type_label}\n"
                f"📛 *Название:* {wallet_type_name}\n"
                f"📊 *Доверие:* {int(wallet_type['confidence'] * 100)}%"
            )
            await update.message.reply_text("🔍 Ищу последнюю транзакцию...")
            last_tx = await tracker.get_last_transaction(address, hours=720)
            if last_tx:
                direction_emoji = "⬇️" if last_tx.get('direction') == 'INCOMING' else "⬆️"
                direction_text = "Получено" if last_tx.get('direction') == 'INCOMING' else "Отправлено"
                token_symbol = last_tx.get('token_symbol', 'UNKNOWN')
                token_amount = last_tx.get('token_amount', Decimal('0'))
                time_str = last_tx.get('time_str', '')
                confirmed = "✅" if last_tx.get('confirmed') else "⏳"
                tx_id = last_tx.get('tx_id', '')
                direction_text = safe_markdown(direction_text)
                time_str = safe_markdown(time_str)
                token_symbol = safe_markdown(token_symbol)
                if token_symbol in ['USDT', 'USDC']:
                    amount_str = f"{token_amount:,.2f}"
                elif token_symbol == 'TRX':
                    amount_str = f"{token_amount:,.6f}"
                else:
                    amount_str = f"{token_amount:,.4f}"
                amount_str = safe_markdown(amount_str)
                tx_info = (
                    f"\n\n🔔 *Последняя транзакция:*\n"
                    f"{direction_emoji} {confirmed} *{time_str}*\n"
                    f"{direction_text} {amount_str} {token_symbol}\n"
                )
                if tx_id:
                    tx_id_display = f"{tx_id[:12]}...{tx_id[-6:]}"
                    tx_info += (
                        f"📝 TXID: `{safe_markdown(tx_id_display)}`\n"
                        f"🔗 [Посмотреть в Tronscan](https://tronscan.org/#/transaction/{safe_markdown(tx_id)})"
                    )
                response += tx_info
        elif network == "SOLANA":
            response += f"\n\n🔗 [Посмотреть в Solscan](https://solscan.io/account/{address})"
        try:
            await update.message.reply_text(
                response,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения с Markdown: {e}")
            simple_response = (
                f"✅ Кошелек успешно добавлен!\n\n"
                f"🌐 Сеть: {network}\n"
                f"🏷️ Название: {clean_nickname}\n"
                f"📍 Адрес: {address}\n\n"
                f"💰 Балансы:\n{balance_summary}"
            )
            if network == "TRON" and 'wallet_type' in locals():
                simple_response += (
                    f"\n\n🧠 Тип кошелька:\n"
                    f"{type_labels.get(wallet_type['type'], '❓')}\n"
                    f"📛 Название: {wallet_type['name']}\n"
                    f"📊 Доверие: {int(wallet_type['confidence'] * 100)}%"
                )
            await update.message.reply_text(
                simple_response,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
    keyboard = [
        [InlineKeyboardButton("📝 Добавить описание сейчас", callback_data=f'add_desc_{address}')],
        [InlineKeyboardButton("➕ Добавить новый кошелёк", callback_data='add_new_wallet')],
    ]
    await update.message.reply_text(
        "Хотите добавить описание для кошелька?\n"
        "Например: «Для работы с биржей», «Личный кошелёк» и т.д.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ConversationHandler.END
async def add_wallet_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username if user.username else "NoUsername"
    log_user_action(user.id, username, "CANCEL_ADD_WALLET")
    await update.message.reply_text("❌ Добавление кошелька отменено.")
    return ConversationHandler.END
async def check_balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username if user.username else "NoUsername"
    log_command(user.id, username, "CHECK_BALANCE")
    user_wallets = tracker.get_user_wallets(update.effective_user.id)
    if not user_wallets:
        await update.message.reply_text("📭 У вас нет отслеживаемых кошельков.")
        return
    await update.message.reply_text("⏳ Проверяю балансы ваших кошельков...")
    updated_count = 0
    for wallet in user_wallets:
        success = await tracker.update_wallet_balances(wallet.address)
        if success:
            updated_count += 1
        await asyncio.sleep(3)  
    log_user_action(user.id, username, "BALANCE_CHECK_COMPLETE", 
                    f"Wallets: {len(user_wallets)}, Updated: {updated_count}")
    if updated_count > 0:
        await update.message.reply_text(f"✅ Проверено {updated_count} кошельков!")
        await my_wallets_command(update, context)
    else:
        await update.message.reply_text("❌ Не удалось проверить балансы. Попробуйте позже.")
async def check_single_balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username if user.username else "NoUsername"
    if not context.args:
        log_command(user.id, username, "BALANCE_SINGLE", "NO_ARGS")
        await update.message.reply_text("Укажите адрес кошелька: /balance <адрес>")
        return
    address = context.args[0]
    log_command(user.id, username, "BALANCE_SINGLE", f"Address: {address}")
    user_wallets = tracker.get_user_wallets(update.effective_user.id)
    if not any(w.address == address for w in user_wallets):
        await update.message.reply_text("❌ Этот кошелек не найден среди ваших отслеживаемых кошельков!")
        return
    await update.message.reply_text(f"⏳ Проверяю баланс кошелька...")
    success = await tracker.update_wallet_balances(address)
    wallet = tracker.tracked_wallets.get(address)
    if wallet and success:
        balance_summary = tracker.get_wallet_balance_summary(wallet)
        last_checked = wallet.last_balance_check.strftime("%d.%m.%Y %H:%M") if wallet.last_balance_check else "Никогда"
        response = (
            f"💰 <b>Балансы кошелька:</b> {wallet.nickname}\n"
            f"📍 <b>Адрес:</b> <code>{wallet.address}</code>\n"
            f"⏰ <b>Последняя проверка:</b> {last_checked}\n\n"
            f"{balance_summary}"
        )
        await update.message.reply_text(
            response,
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text("❌ Ошибка при проверке баланса. Попробуйте позже.")
async def my_wallets_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username if user.username else "NoUsername"
    log_command(user.id, username, "MY_WALLETS")
    user_wallets = tracker.get_user_wallets(update.effective_user.id)
    if not user_wallets:
        await update.message.reply_text("📭 У вас нет отслеживаемых кошельков.")
        return
    await update.message.reply_text(f"📋 Ваши кошельки ({len(user_wallets)}):")
    for i, wallet in enumerate(user_wallets, 1):
        description = wallet.description or "Нет описания"
        last_checked = wallet.last_balance_check.strftime("%d.%m.%Y %H:%M") if wallet.last_balance_check else "Никогда"
        balance_summary = tracker.get_wallet_balance_summary(wallet)
        wallet_text = (
            f"🏷️ <b>{wallet.nickname}</b>\n"
            f"📍 <b>Адрес:</b> <code>{wallet.address}</code>\n"
            f"📝 <b>Описание:</b> {description}\n"
            f"⏰ <b>Проверка баланса:</b> {last_checked}\n\n"
            f"{balance_summary}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        await update.message.reply_text(
            wallet_text,
            parse_mode=ParseMode.HTML
        )
        await asyncio.sleep(3)
    log_user_action(user.id, username, "SHOW_WALLETS", f"Count: {len(user_wallets)}")
    total_coins = sum(len(w.balances) for w in user_wallets if w.balances)
    keyboard = [[InlineKeyboardButton("📋 Показать все адреса", callback_data='show_all_addresses')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    summary_text = (
        f"📊 <b>Итого:</b>\n"
        f"• Кошельков: {len(user_wallets)}\n"
        f"• Всего токенов: {total_coins}\n\n"
        f"💡 <b>Команды:</b>\n"
        f"/check_balance — обновить все балансы\n"
        f"/balance &lt;адрес&gt; — проверить один кошелек\n"
        f"/add_wallet — добавить новый кошелек"
    )
    await update.message.reply_text(
        summary_text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )
async def edit_description_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username if user.username else "NoUsername"
    log_command(user.id, username, "EDIT_DESCRIPTION", f"Args: {' '.join(context.args) if context.args else 'NO_ARGS'}")
    user_wallets = tracker.get_user_wallets(update.effective_user.id)
    if not user_wallets:
        await update.message.reply_text("📭 У вас нет отслеживаемых кошельков.")
        return
    if context.args:
        if len(context.args) >= 2:
            address = context.args[0]
            description = ' '.join(context.args[1:])
            if not any(w.address == address for w in user_wallets):
                await update.message.reply_text("❌ Этот кошелек не найден среди ваших отслеживаемых кошельков!")
                return
            if tracker.update_wallet_description(address, description):
                await update.message.reply_text(f"✅ Описание кошелька успешно обновлено!")
            else:
                await update.message.reply_text("❌ Ошибка при обновлении описания!")
            return
    keyboard = []
    for wallet in user_wallets:
        btn_text = f"{wallet.nickname} ({wallet.address[:6]}...{wallet.address[-4:]})"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f'edit_desc_{wallet.address}')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "📝 Выберите кошелек для изменения описания:",
        reply_markup=reply_markup
    )
async def remove_wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username if user.username else "NoUsername"
    log_command(user.id, username, "REMOVE_WALLET", f"Args: {' '.join(context.args) if context.args else 'NO_ARGS'}")
    if context.args:
        address = context.args[0]
        user_wallets = tracker.get_user_wallets(update.effective_user.id)
        if not any(w.address == address for w in user_wallets):
            await update.message.reply_text("❌ Этот кошелек не найден среди ваших отслеживаемых кошельков!")
            return
        wallet_to_remove = next((w for w in user_wallets if w.address == address), None)
        if wallet_to_remove:
            balance_summary = tracker.get_wallet_balance_summary(wallet_to_remove)
            keyboard = [
                [InlineKeyboardButton("✅ Да, удалить", callback_data=f'confirm_remove_{address}')],
                [InlineKeyboardButton("❌ Нет, отмена", callback_data='cancel_remove')],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"❓ Вы уверены, что хотите удалить кошелек?\n\n"
                f"🏷️ Название: {wallet_to_remove.nickname}\n"
                f"📍 Адрес: {address[:10]}...{address[-6:]}\n"
                f"📝 Описание: {wallet_to_remove.description or 'Нет описания'}\n\n"
                f"💰 Текущие балансы:\n{balance_summary}",
                reply_markup=reply_markup
            )
    else:
        await update.message.reply_text(
            "🗑️ Чтобы удалить кошелек, отправьте команду в формате:\n"
            "/remove_wallet Txxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n\n"
            "Посмотреть список своих кошельков: /my_wallets"
        )
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    username = user.username if user.username else "NoUsername"
    await query.answer()
    data = query.data
    log_user_click(user.id, username, data)    
    if data.startswith('network_'):
        network = data.replace('network_', '').upper()
        context.user_data['network'] = network
        if network == "TRON":
            await query.edit_message_text(
                "📝 Для добавления TRON кошелька отправьте его адрес (начинается с T):\n\n"
                "Пример: `Txxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`\n\n"
                "Отправьте /cancel для отмены.",
                parse_mode=ParseMode.MARKDOWN
            )
            return ADDRESS
        elif network == "SOLANA":
            await query.edit_message_text(
                "📝 Для добавления Solana кошелька отправьте его адрес:\n\n"
                "Пример: `8xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`\n\n"
                "Отправьте /cancel для отмены.",
                parse_mode=ParseMode.MARKDOWN
            )
            return ADDRESS    
    elif data.startswith('add_desc_'):
        address = data.replace('add_desc_', '')
        context.user_data['awaiting_description'] = address
        await query.edit_message_text(
            f"📝 Введите описание для кошелька `{address[:10]}...{address[-6:]}`:",
            parse_mode=ParseMode.MARKDOWN
        )
    elif data == 'add_new_wallet':
        await query.edit_message_text("➕ Добавление нового кошелька...")
        await query.delete_message()
        await add_wallet_start(update, context)
    elif data.startswith('edit_desc_'):
        address = data.replace('edit_desc_', '')
        context.user_data['awaiting_description'] = address
        await query.edit_message_text(
            f"📝 Введите новое описание для кошелька `{address[:10]}...{address[-6:]}`:",
            parse_mode=ParseMode.MARKDOWN
        )
    elif data.startswith('confirm_remove_'):
        address = data.replace('confirm_remove_', '')
        if tracker.remove_wallet(address):
            await query.edit_message_text("✅ Кошелек успешно удален из отслеживания!")
        else:
            await query.edit_message_text("❌ Ошибка при удалении кошелька!")
    elif data == 'cancel_remove':
        await query.edit_message_text("❌ Удаление отменено.")
    elif data == 'check_all_balances':
        await query.edit_message_text("⏳ Начинаю проверку всех балансов...")
        user_wallets = tracker.get_user_wallets(user.id)
        updated_count = 0
        for wallet in user_wallets:
            try:
                success = await tracker.update_wallet_balances(wallet.address)
                if success:
                    updated_count += 1
                await asyncio.sleep(3) 
            except Exception as e:
                logger.error(f"Ошибка при проверке баланса {wallet.address}: {e}")
        if updated_count > 0:
            await query.edit_message_text(f"✅ Проверено {updated_count} из {len(user_wallets)} кошельков!")
            await my_wallets_command(update, context)
        else:
            await query.edit_message_text("❌ Не удалось проверить балансы. Попробуйте позже.")
    elif data == 'show_all_addresses':
        user_wallets = tracker.get_user_wallets(user.id)
        if user_wallets:
            addresses_text = "📋 *Все ваши адреса:*\n\n"
            for i, wallet in enumerate(user_wallets, 1):
                network_emoji = "🌐" if wallet.network == "TRON" else "🔷"
                addresses_text += f"{i}. *{wallet.nickname}* {network_emoji}\n`{wallet.address}`\n\n"
            await query.edit_message_text(
                addresses_text,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.edit_message_text("📭 У вас нет отслеживаемых кошельков.")
    elif data in ['notif_settings', 'check_frequency', 'help']:
        log_user_action(user.id, username, f"SETTINGS_{data.upper()}")
        if data == 'notif_settings':
            await query.edit_message_text("🔔 Настройки уведомлений:\n\n• Уведомлять о новых транзакциях: ✅\n• Уведомлять о балансе: ✅\n• Уведомлять об ошибках: ✅")
        elif data == 'check_frequency':
            await query.edit_message_text("📊 Частота проверок:\n\n• Балансы: Каждые 30 минут\n• Транзакции: Каждые 10 минут")
        elif data == 'help':
            await query.edit_message_text("❓ Помощь:\n\nДля получения помощи напишите /start")
async def handle_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()
    if text.startswith('T') and len(text) == 34:
        await update.message.reply_text(
            "💡 Чтобы добавить кошелек, используйте команду /add_wallet\n"
            f"Или проверьте баланс: /balance {text}"
        )
        return
    if 'awaiting_description' in context.user_data:
        address = context.user_data['awaiting_description']
        description = text
        if tracker.update_wallet_description(address, description):
            await update.message.reply_text(f"✅ Описание обновлено!")
        else:
            await update.message.reply_text("❌ Ошибка!")
        del context.user_data['awaiting_description']
        return
    await start(update, context)
async def check_now_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username if user.username else "NoUsername"
    log_command(user.id, username, "CHECK_NOW")
    await update.message.reply_text("⏳ Проверяю последние транзакции (48 часов)...")  # <-- Уточнение
    user_wallets = tracker.get_user_wallets(user.id)
    if not user_wallets:
        await update.message.reply_text("📭 У вас нет отслеживаемых кошельков.")
        return
    found_transactions = 0
    transactions_shown = 0
    for wallet in user_wallets:
        try:
            transactions = await tracker.check_recent_transactions(wallet.address, hours=48)
            if transactions:
                found_transactions += len(transactions)
                transactions.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
                message_lines = []
                message_lines.append(f"📊 *{wallet.nickname}*")
                message_lines.append(f"📍 `{wallet.address[:10]}...{wallet.address[-6:]}`")
                message_lines.append(f"🔗 [Посмотреть все транзакции в TronScan](https://tronscan.org/#/address/{wallet.address})")
                tx_to_show = transactions[:3]
                if tx_to_show:
                    message_lines.append(f"\n🔍 *Последние {len(tx_to_show)} транзакции:*")
                    for tx in tx_to_show:
                        direction_emoji = "⬇️" if tx.get('direction') == 'INCOMING' else "⬆️"
                        token_symbol = tx.get('token_symbol', 'UNKNOWN')
                        token_amount = tx.get('token_amount', Decimal('0'))
                        time_str = tx.get('time_str', '')
                        if not time_str and tx.get('timestamp'):
                            dt = datetime.fromtimestamp(tx['timestamp'] / 1000)
                            time_str = dt.strftime("%d.%m.%Y %H:%M")
                        if token_symbol in ['USDT', 'USDC']:
                            amount_str = f"{token_amount:,.2f}"
                        elif token_symbol == 'TRX':
                            amount_str = f"{token_amount:,.6f}"
                        elif token_amount >= Decimal('1000'):
                            amount_str = f"{token_amount:,.0f}"
                        elif token_amount >= Decimal('100'):
                            amount_str = f"{token_amount:,.1f}"
                        else:
                            amount_str = f"{token_amount:,.4f}"
                        direction_text = "Получено" if tx.get('direction') == 'INCOMING' else "Отправлено"
                        confirmed = "✅" if tx.get('confirmed', False) else "⏳"
                        tx_id = tx.get('tx_id', '')
                        tx_link = f"https://tronscan.org/#/transaction/{tx_id}" if tx_id else ""
                        
                        if tx_link:
                            message_lines.append(
                                f"{direction_emoji} {confirmed} *{time_str}*: {direction_text} {amount_str} {token_symbol}"
                                f"\n   🔗 [Ссылка на транзакцию]({tx_link})"
                            )
                        else:
                            message_lines.append(
                                f"{direction_emoji} {confirmed} *{time_str}*: {direction_text} {amount_str} {token_symbol}"
                            )
                    message = "\n".join(message_lines)
                    await update.message.reply_text(
                        message,
                        parse_mode=ParseMode.MARKDOWN,
                        disable_web_page_preview=True
                    )
                    transactions_shown += len(tx_to_show)
                    await asyncio.sleep(3)  
        except Exception as e:
            logger.error(f"Ошибка проверки транзакций для {wallet.address}: {e}")
            continue
    if transactions_shown > 0:
        total_wallets = len(user_wallets)
        wallets_with_tx = sum(1 for w in user_wallets if any(w.address == tx.get('to_address') or w.address == tx.get('from_address') 
                                                           for tx in tracker._get_all_transactions_cache().get(w.address, [])))
        summary_text = (
            f"✅ Проверка завершена!\n\n"
            f"📊 *Результаты:*\n"
            f"• Всего кошельков: {total_wallets}\n"
            f"• Кошельков с транзакциями: {wallets_with_tx}\n"
            f"• Показано транзакций: {transactions_shown}\n"
            f"• Всего найдено: {found_transactions}\n\n"
            f"💡 *Совет:*\n"
            f"Используйте ссылки выше для просмотра деталей в TronScan"
        )
        await update.message.reply_text(
            summary_text,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        message_lines = ["📭 *Нет последних транзакций (за 24 часа)*"]
        message_lines.append("\n📋 *Ваши кошельки:*")
        for wallet in user_wallets:
            tron_scan_link = f"https://tronscan.org/#/address/{wallet.address}"
            message_lines.append(f"• {wallet.nickname}: [TronScan]({tron_scan_link})")
        message_lines.append("\n💡 *Возможные причины:*")
        message_lines.append("1. На кошельках не было транзакций за последние 24 часа")
        message_lines.append("2. Кошельки только что добавлены")
        message_lines.append("3. Проблема с подключением к Tron API")
        await update.message.reply_text(
            "\n".join(message_lines),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username if user.username else "NoUsername"
    log_command(user.id, username, "SETTINGS")
    keyboard = [
        [InlineKeyboardButton("🔔 Настройки уведомлений", callback_data='notif_settings')],
        [InlineKeyboardButton("📊 Частота проверок", callback_data='check_frequency')],
        [InlineKeyboardButton("❓ Помощь", callback_data='help')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "⚙️ Настройки бота\n\n"
        "Выберите опцию для настройки:",
        reply_markup=reply_markup
    )
async def set_frequency_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args and context.args[0].isdigit():
        seconds = int(context.args[0])
        if 30 <= seconds <= 3600: 
            await update.message.reply_text(f"✅ Частота проверок установлена: {seconds} секунд")
        else:
            await update.message.reply_text("❌ Частота должна быть от 30 до 3600 секунд")
monitor = None
def signal_handler(signum, frame):
    print("\n🛑 Останавливаю бота...")
    if monitor:
        asyncio.create_task(monitor.stop())
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
def main():
    try:
        application = Application.builder()\
            .token(BOT_TOKEN)\
            .connect_timeout(10)\
            .read_timeout(10)\
            .pool_timeout(10)\
            .build()
        global monitor  
        monitor = TransactionMonitor(
            application=application,
            tracker=tracker,  
            check_interval=300  
        )
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('add_wallet', add_wallet_start)],
            states={
                ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_wallet_address)],
                NICKNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_wallet_nickname)],
            },
            fallbacks=[CommandHandler('cancel', add_wallet_cancel)]
        )
        application.add_handler(CommandHandler("start", start))
        application.add_handler(conv_handler)
        application.add_handler(CommandHandler("set_frequency", set_frequency_command))
        application.add_handler(CommandHandler("my_wallets", my_wallets_command))
        application.add_handler(CommandHandler("check_balance", check_balance_command))
        application.add_handler(CommandHandler("balance", check_single_balance_command))
        application.add_handler(CommandHandler("remove_wallet", remove_wallet_command))
        application.add_handler(CommandHandler("edit_description", edit_description_command))
        application.add_handler(CommandHandler("check_now", check_now_command))
        application.add_handler(CommandHandler("settings", settings_command))
        application.add_handler(CallbackQueryHandler(callback_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_description))
        application.add_handler(CommandHandler("last_tx", last_transaction_command))
        application.add_handler(CommandHandler("force_update", force_update_command))
        application.add_handler(CommandHandler("debug", WalletTracker.debug_wallet_command))
        application.add_handler(CommandHandler("debug_tx", debug_tx_command))
        print("✅ Бот успешно запущен!")
        print("🚀 Запускаю мониторинг транзакций...")
        async def post_init(app: Application):
            await monitor.start()
        application.post_init = post_init
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")
        print(f"❌ Критическая ошибка: {e}")
if __name__ == '__main__':
    main()