import logging
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
import os
import signal

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot_activity.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
ADDRESS, NICKNAME = range(2)

# === ТОКЕН БОТА ===
BOT_TOKEN = "8303361032:AAHJYNuKFN90i5a-2KcjxTMZzl9RaEf9Wac"
# ==================

print("="*50)
print("🤖 ЗАПУСК БОТА")
print("="*50)
print(f"Токен: {BOT_TOKEN[:15]}...")

# Конфигурация
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

def log_user_action(user_id: int, username: str, action: str, details: str = ""):
    """Логирование действий пользователя"""
    log_message = f"👤 USER_ID: {user_id} | USERNAME: @{username} | ACTION: {action}"
    if details:
        log_message += f" | DETAILS: {details}"
    logger.info(log_message)

def log_user_click(user_id: int, username: str, button_data: str):
    """Логирование нажатий кнопок"""
    logger.info(f"👤 USER_ID: {user_id} | USERNAME: @{username} | BUTTON_CLICK: {button_data}")

def log_command(user_id: int, username: str, command: str, args: str = ""):
    """Логирование команд пользователя"""
    log_msg = f"👤 USER_ID: {user_id} | USERNAME: @{username} | COMMAND: {command}"
    if args:
        log_msg += f" | ARGS: {args}"
    logger.info(log_msg)

@dataclass
class WalletBalance:
    """Баланс токена на кошельке"""
    symbol: str
    amount: Decimal
    contract_address: Optional[str] = None
    usd_value: Optional[Decimal] = None
    
    def format_amount(self) -> str:
        """Форматирование суммы для отображения"""
        try:
            if self.symbol == 'TRX':
                return f"{self.amount:,.6f}"
            elif self.symbol in ['USDT', 'USDC']:
                return f"{self.amount:,.2f}"
            elif self.symbol.startswith('TOKEN_'):
                # Для неизвестных токенов показываем больше знаков
                return f"{self.amount:,.6f}"
            else:
                return f"{self.amount:,.4f}"
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка форматирования суммы {self.symbol}: {self.amount}, ошибка: {e}")
            return str(self.amount)
@dataclass
class TrackedWallet:
    """Модель отслеживаемого кошелька"""
    address: str
    user_id: int
    nickname: str
    description: Optional[str] = None
    balances: Dict[str, WalletBalance] = field(default_factory=dict)
    total_usd_value: Decimal = Decimal('0')
    last_checked: Optional[datetime] = None
    last_transaction: Optional[str] = None
    last_balance_check: Optional[datetime] = None

class WalletTracker:
    """Класс для отслеживания транзакций и балансов"""
    
    def __init__(self):
        self.tracked_wallets: Dict[str, TrackedWallet] = {}
        self.load_wallets()
    
    def load_wallets(self):
        """Загрузка кошельков из файла"""
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
                    # Безопасное преобразование user_id
                    user_id_str = str(wallet_data.get('user_id', '0'))
                    try:
                        user_id = int(user_id_str)
                    except (ValueError, TypeError):
                        logger.warning(f"Некорректный user_id для кошелька {addr}: {user_id_str}")
                        continue
                    
                    # Удаляем проверку на максимальный user_id - Telegram использует 64-bit ID
                    # user_id > 2**31 - 1:  # УДАЛЯЕМ ЭТУ ПРОВЕРКУ
                    #     logger.warning(f"Слишком большой user_id для кошелька {addr}: {user_id}")
                    #     continue
                    
                    # Обработка дат
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
                    
                    # Загружаем балансы
                    balances = {}
                    total_usd_value = Decimal('0')
                    
                    if 'balances' in wallet_data:
                        for symbol, balance_data in wallet_data['balances'].items():
                            try:
                                # Безопасное преобразование amount
                                amount_str = balance_data.get('amount', '0')
                                if amount_str is None:
                                    amount_str = '0'
                                
                                amount = Decimal(str(amount_str))
                                
                                # Безопасное преобразование usd_value
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
                    
                    # Безопасное преобразование total_usd_value
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
    
    def save_wallets(self):
        try:
            data = {}
            for addr, wallet in self.tracked_wallets.items():
                # Сериализуем балансы
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
            # Пробуем сохранить хотя бы в упрощенном формате
            try:
                with open('wallets_backup.json', 'w', encoding='utf-8') as f:
                    json.dump({'error': str(e), 'timestamp': datetime.now().isoformat()}, f)
            except:
                pass
    
    def add_wallet(self, address: str, user_id: int, nickname: str, description: str = None):
        """Добавление кошелька для отслеживания"""
        wallet = TrackedWallet(
            address=address,
            user_id=user_id,
            nickname=nickname,
            description=description,
            last_checked=datetime.now(),
            last_balance_check=datetime.now()
        )
        self.tracked_wallets[address] = wallet
        self.save_wallets()
        log_user_action(user_id, "N/A", "ADD_WALLET", f"Address: {address}, Nickname: {nickname}")
    
    def remove_wallet(self, address: str):
        """Удаление кошелька из отслеживания"""
        if address in self.tracked_wallets:
            user_id = self.tracked_wallets[address].user_id
            del self.tracked_wallets[address]
            self.save_wallets()
            log_user_action(user_id, "N/A", "REMOVE_WALLET", f"Address: {address}")
            return True
        return False
    
    def get_user_wallets(self, user_id: int) -> List[TrackedWallet]:
        """Получение всех кошельков пользователя"""
        return [w for w in self.tracked_wallets.values() if w.user_id == user_id]
    
    def update_wallet_description(self, address: str, description: str):
        """Обновление описания кошелька"""
        if address in self.tracked_wallets:
            user_id = self.tracked_wallets[address].user_id
            self.tracked_wallets[address].description = description
            self.save_wallets()
            log_user_action(user_id, "N/A", "UPDATE_DESCRIPTION", f"Address: {address}")
            return True
        return False
    
    async def get_trx_balance(self, address: str) -> Decimal:
        """Получение баланса TRX"""
        try:
            url = f"{TRON_NETWORK}/v1/accounts/{address}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('data'):
                            account_data = data['data'][0]
                            balance_sun = account_data.get('balance', 0)
                            # Конвертируем из sun в TRX (1 TRX = 1,000,000 sun)
                            balance_trx = Decimal(str(balance_sun)) / Decimal('1000000')
                            logger.info(f"TRX баланс для {address}: {balance_sun} sun = {balance_trx} TRX")
                            return balance_trx
                    logger.error(f"API ошибка при получении TRX баланса: {response.status}")
                    return Decimal('0')
                        
        except Exception as e:
            logger.error(f"Ошибка получения TRX баланса: {e}")
            return Decimal('0')
        
    async def get_trc20_balances_alternative(self, address: str) -> Dict[str, WalletBalance]:
        """Альтернативный метод получения TRC20 балансов"""
        try:
            # Этот метод получает балансы напрямую из данных аккаунта
            url = f"{TRON_NETWORK}/v1/accounts/{address}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if not data.get('data'):
                            return {}
                        
                        account_data = data['data'][0]
                        result = {}
                        
                        # Проверяем наличие TRC20 токенов
                        if 'trc20' in account_data:
                            trc20_list = account_data['trc20']
                            
                            for token_entry in trc20_list:
                                for contract_address, raw_amount in token_entry.items():
                                    # Ищем в наших известных контрактах
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
                        
                        return result
                    else:
                        return {}
                        
        except Exception as e:
            logger.error(f"Ошибка в альтернативном методе получения балансов: {e}")
            return {}

    async def get_all_trc20_balances(self, address: str) -> Dict[str, WalletBalance]:
        """Получение всех TRC20 балансов кошелька"""
        try:
            url = f"{TRON_NETWORK}/v1/accounts/{address}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if not data.get('data'):
                            logger.warning(f"Нет данных в ответе API для адреса {address}")
                            return {}
                        
                        account_data = data['data'][0]
                        result = {}
                        
                        # Получаем список TRC20 токенов
                        trc20_list = account_data.get('trc20', [])
                        
                        logger.info(f"Найдено {len(trc20_list)} TRC20 записей для адреса {address}")
                        
                        # Обрабатываем каждый TRC20 токен
                        for token_entry in trc20_list:
                            for contract_address, raw_amount in token_entry.items():
                                # Преобразуем сырое значение в строку
                                raw_amount_str = str(raw_amount)
                                
                                # Ищем токен в нашем списке известных контрактов
                                token_found = False
                                for token_name, token_info in TRC20_CONTRACTS.items():
                                    if contract_address.lower() == token_info['address'].lower():
                                        decimals = token_info['decimals']
                                        
                                        try:
                                            # Конвертируем с учетом decimals
                                            amount = Decimal(raw_amount_str) / Decimal(f"1e{decimals}")
                                            
                                            if amount > Decimal('0'):
                                                result[token_name] = WalletBalance(
                                                    symbol=token_info['symbol'],
                                                    amount=amount,
                                                    contract_address=contract_address
                                                )
                                                logger.info(f"Найден известный токен: {token_name} = {amount}")
                                        except Exception as e:
                                            logger.warning(f"Ошибка конвертации баланса {token_name}: {e}")
                                        
                                        token_found = True
                                        break
                                
                                # Если токен не найден в нашем списке, все равно добавляем его
                                if not token_found:
                                    try:
                                        # Пробуем определить decimals (по умолчанию 6 для TRC20)
                                        decimals = 6
                                        amount = Decimal(raw_amount_str) / Decimal(f"1e{decimals}")
                                        
                                        if amount > Decimal('0'):
                                            # Создаем имя токена из первых 6 символов адреса
                                            token_symbol = f"TOKEN_{contract_address[:6]}"
                                            result[token_symbol] = WalletBalance(
                                                symbol=token_symbol,
                                                amount=amount,
                                                contract_address=contract_address
                                            )
                                            logger.info(f"Найден неизвестный токен: {contract_address} = {amount}")
                                    except Exception as e:
                                        logger.warning(f"Ошибка обработки неизвестного токена {contract_address}: {e}")
                        
                        logger.info(f"Всего обработано {len(result)} токенов для адреса {address}")
                        return result
                        
                    else:
                        logger.error(f"API ошибка: {response.status} для адреса {address}")
                        return {}
                        
        except Exception as e:
            logger.error(f"Критическая ошибка получения TRC20 балансов для {address}: {e}", exc_info=True)
            return {}
    
    async def update_wallet_balances(self, address: str) -> bool:
        """Обновление балансов кошелька"""
        try:
            wallet = self.tracked_wallets.get(address)
            if not wallet:
                return False
            
            logger.info(f"Обновление балансов для кошелька {address}")
            
            # Очищаем старые балансы
            wallet.balances.clear()
            
            # Получаем баланс TRX
            trx_balance = await self.get_trx_balance(address)
            if trx_balance > Decimal('0'):
                wallet.balances['TRX'] = WalletBalance(
                    symbol='TRX',
                    amount=trx_balance,
                    contract_address=None
                )
            
            # Пробуем оба метода получения TRC20 балансов
            trc20_balances = await self.get_all_trc20_balances(address)
            
            # Если первый метод не сработал, пробуем альтернативный
            if not trc20_balances:
                logger.info(f"Первый метод не сработал, пробую альтернативный для {address}")
                trc20_balances = await self.get_trc20_balances_alternative(address)
            
            # Добавляем TRC20 балансы
            for token_name, balance in trc20_balances.items():
                wallet.balances[token_name] = balance
            
            # Обновляем время проверки баланса
            wallet.last_balance_check = datetime.now()
            
            # Сохраняем в файл
            self.save_wallets()
            
            logger.info(f"Балансы для кошелька {address} обновлены. Найдено токенов: {len(wallet.balances)}")
            log_user_action(wallet.user_id, "N/A", "UPDATE_BALANCE", 
                        f"Address: {address}, Tokens: {len(wallet.balances)}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обновления балансов для {address}: {e}")
            return False
    
    async def check_all_balances(self):
        """Проверка балансов для всех кошельков"""
        for i, address in enumerate(list(self.tracked_wallets.keys())):
            await self.update_wallet_balances(address)
            if i % 5 == 0 and i > 0:
                await asyncio.sleep(2)  # Задержка каждые 5 кошельков
            else:
                await asyncio.sleep(0.5)  # Меньшая задержка между запросами
        
    def get_wallet_balance_summary(self, wallet: TrackedWallet) -> str:
        """Получение текстового представления балансов кошелька"""
        if not wallet.balances:
            return "💰 На кошельке нет средств или балансы еще не проверялись.\nИспользуйте /check_balance для проверки."
        
        # Группируем токены
        trx_balance = []
        known_tokens = []
        unknown_tokens = []
        
        for symbol, balance in wallet.balances.items():
            if symbol == 'TRX':
                trx_balance.append((symbol, balance))
            elif symbol in TRC20_CONTRACTS:
                known_tokens.append((symbol, balance))
            else:
                unknown_tokens.append((symbol, balance))
        
        lines = []
        
        # TRX - БЕЗ Markdown
        if trx_balance:
            lines.append("🌐 TRX (Native):")
            for symbol, balance in trx_balance:
                lines.append(f"  • {symbol}: {balance.format_amount()}")
        
        # Известные TRC20 токены - БЕЗ Markdown
        if known_tokens:
            lines.append("\n💵 TRC20 Токены:")
            for symbol, balance in known_tokens:
                lines.append(f"  • {symbol}: {balance.format_amount()}")
        
        # Неизвестные токены (сокращенный адрес) - БЕЗ Markdown
        if unknown_tokens:
            lines.append("\n🔍 Другие токены:")
            for symbol, balance in unknown_tokens:
                # Для неизвестных токенов показываем сокращенный адрес
                if balance.contract_address:
                    short_addr = f"{balance.contract_address[:6]}...{balance.contract_address[-4:]}"
                    lines.append(f"  • {symbol} ({short_addr}): {balance.format_amount()}")
                else:
                    lines.append(f"  • {symbol}: {balance.format_amount()}")
        
        return "\n".join(lines) if lines else "Балансы не найдены"

# Инициализация трекера
tracker = WalletTracker()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    username = user.username if user.username else "NoUsername"
    
    # Логирование команды старт
    log_command(user.id, username, "START")
    
    welcome_text = f"""
👋 Привет, {user.first_name}!

Я бот для отслеживания балансов и транзакций TRC20 кошельков.

📋 ДОСТУПНЫЕ КОМАНДЫ:
/add_wallet - Добавить кошелек для отслеживания
/my_wallets - Мои отслеживаемые кошельки с балансами
/check_balance - Проверить балансы кошельков
/remove_wallet - Удалить кошелек из отслеживания
/check_now - Проверить транзакции сейчас
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
    """Начало процесса добавления кошелька"""
    user = update.effective_user
    username = user.username if user.username else "NoUsername"
    
    # Логирование начала добавления кошелька
    log_command(user.id, username, "ADD_WALLET_START")
    
    await update.message.reply_text(
        "📝 Введите TRON адрес кошелька (начинается с T, 34 символа):\n"
        "Пример: `TQoLjC5RqAJYxqZv8kUeS5S5S5S5S5S5S5S5S5S5`\n\n"
        "ℹ️ Адрес можно найти в вашем TRON кошельке."
    )
    return ADDRESS

async def add_wallet_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение адреса кошелька"""
    user = update.effective_user
    username = user.username if user.username else "NoUsername"
    address = update.message.text.strip()
    
    # Логирование ввода адреса
    log_user_action(user.id, username, "ENTER_ADDRESS", f"Address: {address}")
    
    # Простая валидация адреса TRON
    if not address.startswith('T') or len(address) != 34:
        await update.message.reply_text(
            "❌ Неверный формат TRON адреса!\n"
            "Адрес должен начинаться с 'T' и содержать 34 символа.\n"
            "Попробуйте еще раз:"
        )
        return ADDRESS
    
    # Проверяем, не добавлен ли уже кошелек
    user_wallets = tracker.get_user_wallets(update.effective_user.id)
    if any(w.address == address for w in user_wallets):
        await update.message.reply_text("❌ Этот кошелек уже отслеживается! Введите другой адрес:")
        return ADDRESS
    
    context.user_data['address'] = address
    await update.message.reply_text(
        "✅ Адрес принят!\n\n"
        "📝 Теперь введите название для этого кошелька:\n"
        "Например: 'Мой основной', 'Для торговли', 'Кошелек №1'"
    )
    return NICKNAME

async def add_wallet_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение названия и описания кошелька"""
    user = update.effective_user
    username = user.username if user.username else "NoUsername"
    nickname = update.message.text.strip()
    address = context.user_data.get('address')
    
    # Логирование ввода названия кошелька
    log_user_action(user.id, username, "ENTER_NICKNAME", f"Address: {address}, Nickname: {nickname}")
    
    if not address:
        await update.message.reply_text("❌ Ошибка: адрес не найден. Начните заново командой /add_wallet")
        return ConversationHandler.END
    
    # Добавляем кошелек
    tracker.add_wallet(
        address=address,
        user_id=update.effective_user.id,
        nickname=nickname,
        description=None
    )
    
    # Сразу проверяем баланс нового кошелька
    await update.message.reply_text("⏳ Проверяю баланс нового кошелька...")
    success = await tracker.update_wallet_balances(address)
    
    # Получаем обновленный кошелек с балансами
    wallet = tracker.tracked_wallets.get(address)
    
    if not success or not wallet:
        await update.message.reply_text(
            f"⚠️ Кошелек добавлен, но не удалось проверить баланс.\n"
            f"Попробуйте позже командой /check_balance"
        )
    else:
        balance_summary = tracker.get_wallet_balance_summary(wallet)
        
        await update.message.reply_text(
            f"✅ Кошелек успешно добавлен!\n\n"
            f"🏷️ Название: {nickname}\n"
            f"📍 Адрес: {address}\n\n"
            f"💰 Балансы:\n{balance_summary}"
            # Убрали parse_mode
        )
    
    # Предлагаем добавить описание
    keyboard = [
        [InlineKeyboardButton("📝 Добавить описание сейчас", callback_data=f'add_desc_{address}')],
        [InlineKeyboardButton("➡️ Пропустить", callback_data=f'skip_desc_{address}')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Хотите добавить описание для кошелька?\n"
        "Например: 'Для работы с биржей', 'Личный кошелек' и т.д.",
        reply_markup=reply_markup
    )
    
    return ConversationHandler.END

async def add_wallet_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена добавления кошелька"""
    user = update.effective_user
    username = user.username if user.username else "NoUsername"
    
    # Логирование отмены
    log_user_action(user.id, username, "CANCEL_ADD_WALLET")
    
    await update.message.reply_text("❌ Добавление кошелька отменено.")
    return ConversationHandler.END

async def check_balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка балансов всех кошельков пользователя"""
    user = update.effective_user
    username = user.username if user.username else "NoUsername"
    
    # Логирование команды
    log_command(user.id, username, "CHECK_BALANCE")
    
    user_wallets = tracker.get_user_wallets(update.effective_user.id)
    
    if not user_wallets:
        await update.message.reply_text("📭 У вас нет отслеживаемых кошельков.")
        return
    
    await update.message.reply_text("⏳ Проверяю балансы ваших кошельков...")
    
    # Проверяем балансы для всех кошельков пользователя
    updated_count = 0
    for wallet in user_wallets:
        success = await tracker.update_wallet_balances(wallet.address)
        if success:
            updated_count += 1
        await asyncio.sleep(1)  # Задержка между запросами
    
    # Логирование результата проверки
    log_user_action(user.id, username, "BALANCE_CHECK_COMPLETE", 
                    f"Wallets: {len(user_wallets)}, Updated: {updated_count}")
    
    # Показываем результаты
    if updated_count > 0:
        await update.message.reply_text(f"✅ Проверено {updated_count} кошельков!")
        await my_wallets_command(update, context)
    else:
        await update.message.reply_text("❌ Не удалось проверить балансы. Попробуйте позже.")

async def check_single_balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка баланса конкретного кошелька"""
    user = update.effective_user
    username = user.username if user.username else "NoUsername"
    
    if not context.args:
        # Логирование запроса без аргументов
        log_command(user.id, username, "BALANCE_SINGLE", "NO_ARGS")
        await update.message.reply_text("Укажите адрес кошелька: /balance <адрес>")
        return
    
    address = context.args[0]
    # Логирование запроса с аргументами
    log_command(user.id, username, "BALANCE_SINGLE", f"Address: {address}")
    
    user_wallets = tracker.get_user_wallets(update.effective_user.id)
    
    # Проверяем, принадлежит ли кошелек пользователю
    if not any(w.address == address for w in user_wallets):
        await update.message.reply_text("❌ Этот кошелек не найден среди ваших отслеживаемых кошельков!")
        return
    
    await update.message.reply_text(f"⏳ Проверяю баланс кошелька {address[:10]}...")
    
    # Обновляем баланс
    success = await tracker.update_wallet_balances(address)
    
    # Получаем кошелек и балансы
    wallet = tracker.tracked_wallets.get(address)
    if wallet and success:
        balance_summary = tracker.get_wallet_balance_summary(wallet)
        last_checked = wallet.last_balance_check.strftime("%d.%m.%Y %H:%M") if wallet.last_balance_check else "Никогда"
        
        response = (
            f"💰 Балансы кошелька: {wallet.nickname}\n"
            f"📍 Адрес: {address}\n"
            f"⏰ Последняя проверка: {last_checked}\n\n"
            f"{balance_summary}"
        )
        
        await update.message.reply_text(response)  # Без parse_mode
    else:
        await update.message.reply_text("❌ Ошибка при проверке баланса. Попробуйте позже.")

async def my_wallets_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать все отслеживаемые кошельки пользователя с балансами"""
    user = update.effective_user
    username = user.username if user.username else "NoUsername"
    
    # Логирование команды
    log_command(user.id, username, "MY_WALLETS")
    
    user_wallets = tracker.get_user_wallets(update.effective_user.id)
    
    if not user_wallets:
        await update.message.reply_text("📭 У вас нет отслеживаемых кошельков.")
        return
    
    await update.message.reply_text(f"📋 Ваши кошельки ({len(user_wallets)}):")
    
    for i, wallet in enumerate(user_wallets, 1):
        description = wallet.description or "Нет описания"
        last_checked = wallet.last_balance_check.strftime("%d.%m.%Y %H:%M") if wallet.last_balance_check else "Никогда"
        
        # Формируем сообщение для кошелька
        balance_summary = tracker.get_wallet_balance_summary(wallet)
        
        # БЕЗ Markdown разметки, используем обычный текст
        wallet_text = (
            f"🏷️ {wallet.nickname}\n"
            f"📍 Адрес: {wallet.address[:10]}...{wallet.address[-6:]}\n"
            f"📝 Описание: {description}\n"
            f"⏰ Проверка баланса: {last_checked}\n\n"
            f"{balance_summary}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        
        await update.message.reply_text(wallet_text)  # Убрали parse_mode
        await asyncio.sleep(0.5)  # Небольшая задержка между сообщениями
    
    # Логирование показа кошельков
    log_user_action(user.id, username, "SHOW_WALLETS", f"Count: {len(user_wallets)}")
    
    # Итоговое сообщение
    total_coins = sum(len(w.balances) for w in user_wallets if w.balances)
    
    await update.message.reply_text(
        f"📊 Итого:\n"
        f"• Кошельков: {len(user_wallets)}\n"
        f"• Всего токенов: {total_coins}\n\n"
        f"💡 Команды:\n"
        f"/check_balance - обновить все балансы\n"
        f"/balance <адрес> - проверить один кошелек\n"
        f"/add_wallet - добавить новый кошелек"
        # Убрали parse_mode
    )

async def edit_description_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Изменение описания кошелька"""
    user = update.effective_user
    username = user.username if user.username else "NoUsername"
    
    # Логирование команды
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
    
    # Если нет аргументов, показываем список кошельков
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
    """Удаление кошелька из отслеживания"""
    user = update.effective_user
    username = user.username if user.username else "NoUsername"
    
    # Логирование команды
    log_command(user.id, username, "REMOVE_WALLET", f"Args: {' '.join(context.args) if context.args else 'NO_ARGS'}")
    
    if context.args:
        address = context.args[0]
        
        user_wallets = tracker.get_user_wallets(update.effective_user.id)
        if not any(w.address == address for w in user_wallets):
            await update.message.reply_text("❌ Этот кошелек не найден среди ваших отслеживаемых кошельков!")
            return
        
        wallet_to_remove = next((w for w in user_wallets if w.address == address), None)
        
        if wallet_to_remove:
            # Показываем баланс перед удалением
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
                # Убрали parse_mode
            )
    else:
        await update.message.reply_text(
            "🗑️ Чтобы удалить кошелек, отправьте команду в формате:\n"
            "/remove_wallet Txxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n\n"
            "Посмотреть список своих кошельков: /my_wallets"
            # Убрали parse_mode
        )

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик inline кнопок"""
    query = update.callback_query
    user = query.from_user
    username = user.username if user.username else "NoUsername"
    
    await query.answer()
    
    data = query.data
    
    # Логирование нажатия кнопки
    log_user_click(user.id, username, data)
    
    if data.startswith('add_desc_'):
        address = data.replace('add_desc_', '')
        context.user_data['awaiting_description'] = address
        await query.edit_message_text(
            f"📝 Введите описание для кошелька `{address[:10]}...{address[-6:]}`:",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data.startswith('skip_desc_'):
        address = data.replace('skip_desc_', '')
        await query.edit_message_text(
            f"✅ Кошелек добавлен без описания.\n"
            f"Можете добавить описание позже командой /edit_description",
            parse_mode=ParseMode.MARKDOWN
        )
    
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
                await asyncio.sleep(1)  # Задержка между запросами
            except Exception as e:
                logger.error(f"Ошибка при проверке баланса {wallet.address}: {e}")
        
        if updated_count > 0:
            await query.edit_message_text(f"✅ Проверено {updated_count} из {len(user_wallets)} кошельков!")
            # Показываем обновленные кошельки
            await my_wallets_command(update, context)
        else:
            await query.edit_message_text("❌ Не удалось проверить балансы. Попробуйте позже.")
    elif data in ['notif_settings', 'check_frequency', 'help']:
        # Логирование нажатия на кнопки настроек
        log_user_action(user.id, username, f"SETTINGS_{data.upper()}")
        if data == 'notif_settings':
            await query.edit_message_text("🔔 Настройки уведомлений:\n\n• Уведомлять о новых транзакциях: ✅\n• Уведомлять о балансе: ✅\n• Уведомлять об ошибках: ✅")
        elif data == 'check_frequency':
            await query.edit_message_text("📊 Частота проверок:\n\n• Балансы: Каждые 30 минут\n• Транзакции: Каждые 10 минут")
        elif data == 'help':
            await query.edit_message_text("❓ Помощь:\n\nДля получения помощи напишите /start")

async def handle_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ввода описания"""
    user = update.effective_user
    username = user.username if user.username else "NoUsername"
    
    if 'awaiting_description' in context.user_data:
        address = context.user_data['awaiting_description']
        description = update.message.text.strip()
        
        # Логирование ввода описания
        log_user_action(user.id, username, "ENTER_DESCRIPTION", 
                       f"Address: {address}, Description: {description[:50]}...")
        
        if tracker.update_wallet_description(address, description):
            await update.message.reply_text(f"✅ Описание для кошелька успешно обновлено!")
        else:
            await update.message.reply_text("❌ Ошибка при обновлении описания!")
        
        del context.user_data['awaiting_description']

async def check_now_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ручная проверка транзакций"""
    user = update.effective_user
    username = user.username if user.username else "NoUsername"
    
    # Логирование команды
    log_command(user.id, username, "CHECK_NOW")
    
    await update.message.reply_text("⏳ Проверяю транзакции...")
    # Здесь должна быть ваша логика проверки транзакций
    await update.message.reply_text("🔄 Новых транзакций не найдено.")

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Настройки бота"""
    user = update.effective_user
    username = user.username if user.username else "NoUsername"
    
    # Логирование команды
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

def main():
    """Основная функция запуска бота"""
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        # ConversationHandler для добавления кошелька
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('add_wallet', add_wallet_start)],
            states={
                ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_wallet_address)],
                NICKNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_wallet_nickname)],
            },
            fallbacks=[CommandHandler('cancel', add_wallet_cancel)]
        )
        
        # Добавление обработчиков команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(conv_handler)
        application.add_handler(CommandHandler("my_wallets", my_wallets_command))
        application.add_handler(CommandHandler("check_balance", check_balance_command))
        application.add_handler(CommandHandler("balance", check_single_balance_command))
        application.add_handler(CommandHandler("remove_wallet", remove_wallet_command))
        application.add_handler(CommandHandler("edit_description", edit_description_command))
        application.add_handler(CommandHandler("check_now", check_now_command))
        application.add_handler(CommandHandler("settings", settings_command))
        application.add_handler(CallbackQueryHandler(callback_handler))
        
        # Обработчик для ввода описания
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_description))
        
        # Обработчик для старта
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start))
        
        print("✅ Бот успешно запущен!")
        print("📱 Перейдите в Telegram и найдите вашего бота")
        print("💬 Отправьте команду /start")
        print("📝 Логи будут сохраняться в файл: bot_activity.log")
        print("="*50 + "\n")
        
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")
        print(f"❌ Критическая ошибка: {e}")

if __name__ == '__main__':
    main()