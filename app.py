import time
from flask import Flask, request
from flask_socketio import SocketIO, emit
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import smbus2 as smbus
cred = credentials.Certificate("CERTIFICAT_ICI")

firebase_admin.initialize_app(cred, {
    'databaseURL': "URL_ICI"    
})

# Define some device parameters
I2C_ADDR  = 0x27 # I2C device address
LCD_WIDTH = 16   # Maximum characters per line

# Define some device constants
LCD_CHR = 1 # Mode - Sending data
LCD_CMD = 0 # Mode - Sending command

LCD_LINE_1 = 0x80 # LCD RAM address for the 1st line
LCD_LINE_2 = 0xC0 # LCD RAM address for the 2nd line
LCD_LINE_3 = 0x94 # LCD RAM address for the 3rd line
LCD_LINE_4 = 0xD4 # LCD RAM address for the 4th line

LCD_BACKLIGHT  = 0x08  # On
#LCD_BACKLIGHT = 0x00  # Off

ENABLE = 0b00000100 # Enable bit

# Timing constants
E_PULSE = 0.0005
E_DELAY = 0.0005

#Open I2C interface
#bus = smbus.SMBus(0)  # Rev 1 Pi uses 0
bus = smbus.SMBus(3) # Rev 2 Pi uses 1

list_of_prices = []
list_of_products = []

def lcd_init():
  # Initialise display
  lcd_byte(0x33,LCD_CMD) # 110011 Initialise
  lcd_byte(0x32,LCD_CMD) # 110010 Initialise
  lcd_byte(0x06,LCD_CMD) # 000110 Cursor move direction
  lcd_byte(0x0C,LCD_CMD) # 001100 Display On,Cursor Off, Blink Off 
  lcd_byte(0x28,LCD_CMD) # 101000 Data length, number of lines, font size
  lcd_byte(0x01,LCD_CMD) # 000001 Clear display
  time.sleep(E_DELAY)

def lcd_byte(bits, mode):
  # Send byte to data pins
  # bits = the data
  # mode = 1 for data
  #        0 for command

  bits_high = mode | (bits & 0xF0) | LCD_BACKLIGHT
  bits_low = mode | ((bits<<4) & 0xF0) | LCD_BACKLIGHT

  # High bits
  bus.write_byte(I2C_ADDR, bits_high)
  lcd_toggle_enable(bits_high)

  # Low bits
  bus.write_byte(I2C_ADDR, bits_low)
  lcd_toggle_enable(bits_low)

def lcd_toggle_enable(bits):
  # Toggle enable
  time.sleep(E_DELAY)
  bus.write_byte(I2C_ADDR, (bits | ENABLE))
  time.sleep(E_PULSE)
  bus.write_byte(I2C_ADDR,(bits & ~ENABLE))
  time.sleep(E_DELAY)

def lcd_string(message,line):
  # Send string to display

  message = message.ljust(LCD_WIDTH," ")

  lcd_byte(line, LCD_CMD)

  for i in range(LCD_WIDTH):
    lcd_byte(ord(message[i]),LCD_CHR)


    




app = Flask(__name__)
socketio = SocketIO(app)

def format_price(price):
  return "{:,.2f}$".format(price).replace(".", ",")

def transform_name(string):
   
  # split the string into words using the split() function

  if len(string) <= 11:
      return string

  words = string.split()

  # create an empty list to store the transformed words
  transformed_words = []

  # loop through each word and transform it
  for word in words:
      if len(word) > 5:
          transformed_word = word[:5]
      else:
          transformed_word = word
      transformed_words.append(transformed_word)

  # join the transformed words back into a string using the join() function
  transformed_string = " ".join(transformed_words)

  return transformed_string  


@app.route('/', methods=['POST'])
def receive_string():
    global list_of_prices
    string = request.get_data(as_text=True)
    #print("Product: "+string)

    


    ref = db.reference(f'products/{string}')
    #print(ref.get())
    value = ref.get()

    list_of_prices.append(float(value['price']))

    value['number'] = string
    print(str(value['price']))

    list_of_products.append(value)

    #print(list_of_products)

    emit('receive_total', format_price(sum(list_of_prices)), broadcast=True, namespace="")

    


    emit('receive_string', list_of_products, broadcast=True, namespace="")

    #


   
    
    lcd_string(f"{transform_name(value['name'])} {format_price(value['price'])}", LCD_LINE_1)
    lcd_string(f"Total : {format_price(sum(list_of_prices))}", LCD_LINE_2)  


    #time.sleep(8)
    #lcd_string(f" ", LCD_LINE_1)
    #get the price from the Firebase database using the product number (string) as the key
    #then, instead of sending just the number with the emit() function,
    #we'll send the number but also its price so we can display the price to the UI (Desktop App)
    return 'Received string: {}'.format(string)



@app.route('/clear_total', methods=['POST'])
def clear_total():  
  print("Clearing the total list...")
  global list_of_prices
  global list_of_products
  list_of_prices = []
  list_of_products = []
  lcd_string(" ", LCD_LINE_1)
    #print(str(sum(list_of_prices)))
  lcd_string(" ", LCD_LINE_2)     
  return ''

@socketio.on('connect')
def handle_connect():
    print('Client connected')

    return ''

    

if __name__ == '__main__':
    try:
        lcd_init()
    except KeyboardInterrupt:
        pass
    finally:
        lcd_byte(0x01, LCD_CMD)
    app.run(host='0.0.0.0', port=5005)
    #emit('receive_string', "string", broadcast=True, namespace="")
    #socketio.run(app, host='0.0.0.0', port=5004)

