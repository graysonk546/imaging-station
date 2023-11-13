from PyQt5.QtWidgets import QDoubleSpinBox, QLineEdit
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QValidator
from fractions import Fraction

class FractionalLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

    def keyPressEvent(self, event):
        if event.text() == '/':
            # Handle the "/" key to insert a '/' character
            cursor = self.cursorPosition()
            text = self.text()
            self.setText(text[:cursor] + '/' + text[cursor:])
            self.setCursorPosition(cursor + 1)
        else:
            super().keyPressEvent(event)

class CustomDoubleSpinBox(QDoubleSpinBox):
    def __init__(self):
        super().__init__()
        self.setDecimals(5)  # Max num of decimals for 1/32 = 0.03125
        self.setRange(0.0, 1000.0)  # To accomodate input of large fractions eg 500/32
        self.setSingleStep(1.0 / 32)  # Set your desired step
        
        # Use a custom line edit widget
        self.setLineEdit(FractionalLineEdit())

    def validate(self, input_text, pos):
        # Custom validation function to allow fractions with '/' and decimals
        
        # If the input contains '/', attempt to convert it to a Fraction
        if '/' in input_text:
            try:
                Fraction(input_text)
                return (QValidator.Acceptable, input_text, pos)
            except ValueError:
                pass
            except ZeroDivisionError:
                print("0 division error occurred, replacing value with 0.")
                input_text = "0"

        # For other cases, use the default validator
        return super().validate(input_text, pos)

    def valueFromText(self, text):
        # Use regular expressions to check if the input is a fraction or a decimal
        if '/' in text:
            # If it's a fraction, convert it to a decimal
            try:
                fraction = Fraction(text)
            except ZeroDivisionError:
                print("0 division error occurred, replacing value with 0.")
                fraction = Fraction("0")
            value = float(fraction)
        else:
            # If it's a decimal, parse it as a float
            value = float(text)

        # Round to the nearest 1/32
        value = round(value * 32) / 32

        return value

    def textFromValue(self, value):
        # Convert the decimal value to a fraction of 32
        fraction = Fraction(value).limit_denominator(32)
        numerator, denominator = fraction.numerator, fraction.denominator

        # Display the fraction as text
        if denominator == 1:
            return str(numerator)
        else:
            return f"{numerator}/{denominator}"
