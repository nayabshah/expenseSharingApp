from marshmallow import Schema, fields, validates, ValidationError, validate
from flask import Flask, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
import xlsxwriter
from functools import wraps

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///database.db'
app.config['JWT_SECRET_KEY'] = 'your_super_secret_jwt_key'
db = SQLAlchemy(app)
# Initialize JWTManager


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # User's name
    email = db.Column(db.String(120), unique=True,
                      nullable=False)  # User's email
    mobile_number = db.Column(
        db.String(15), nullable=False)  # User's mobile number

# Expense Model


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200))
    amount = db.Column(db.Float)


# Expense Participants Model (For splitting)


class ExpenseParticipant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, db.ForeignKey('expense.id'))
    amount_paid = db.Column(db.Float)


class UserSchema(Schema):
    name = fields.Str(
        required=True, validate=validate.Length(min=3, max=80))
    email = fields.Email(required=True)

    mobile_number = fields.Str(
        required=True, validate=validate.Length(max=10))


class ExpenseSchema(Schema):
    description = fields.Str(required=True)
    amount = fields.Float(required=True, validate=lambda val: val > 0)
    # List of participant user IDs
    participants = fields.List(fields.Int(), required=True)


class SplitPercentageSchema(Schema):

    percentage = fields.Float(required=True)

    @validates('percentage')
    def validate_percentage(self, value):
        if value <= 0 or value > 100:
            raise ValidationError(
                "Percentage must be greater than 0 and less than or equal to 100.")


@app.route('/createUser', methods=['POST'])
def createUser():
    data = request.get_json()
    user_schema = UserSchema()
    errors = user_schema.validate(data)

    if errors:
        return jsonify(errors), 400

    # Check if the user already exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({"error": "User already exists"}), 400

    # Create new user
    new_user = User(
        name=data['name'],
        email=data['email'],
        mobile_number=data['mobile_number'],

    )
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User created successfully"}), 201


@app.route('/getUser', methods=['POST'])
def getUser():
    data = request.get_json()

    if not data or 'email' not in data:
        # Valid return: body, status
        return jsonify({"error": "Email is required"}), 400

    user = User.query.filter_by(email=data['email']).first()

    if user:
        # Convert the User object to a dictionary
        user_data = {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "mobile": user.mobile_number
        }
        return jsonify(user_data), 200  # Valid return: body, status
    else:
        # Valid return: body, status
        return jsonify({"error": "User not found"}), 404


@app.route('/expenses', methods=['POST'])
def add_expense():
    data = request.get_json()

    # Create new expense linked to the authenticated user
    new_expense = Expense(
        description=data['description'],
        amount=data['amount'],
    )

    db.session.add(new_expense)
    db.session.commit()

    return jsonify({"message": "Expense added successfully"}), 201


@app.route('/balancesheet', methods=['GET'])
def download_balance_sheet(user):
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet()

    worksheet.write('A1', 'User')
    worksheet.write('B1', 'Amount Owed')

    # Fetch and write balance details for the authenticated user
    expenses = Expense.query.filter_by(user_id=user.id).all()

    row = 1
    for expense in expenses:
        worksheet.write(row, 0, user.name)
        worksheet.write(row, 1, expense.amount)
        row += 1

    workbook.close()
    output.seek(0)

    return send_file(output, as_attachment=True, mimetype='application/vnd.ms-excel',
                     attachment_filename='balance_sheet.xlsx')


@app.route('/expenses/<int:id>/split', methods=['POST'])
def split_expense(id):
    expense = Expense.query.get(id)
    split_method = request.json.get('split_method')
    participants = request.json.get('participants')

    if split_method == 'exact':
        for p in participants:
            # Validate that the exact amounts add up to the total_amount
            pass
    elif split_method == 'percentage':
        for p in participants:
            # Validate that percentages add up to 100
            pass
    elif split_method == 'equal':
        # Split total_amount equally among participants
        equal_amount = expense.total_amount / len(participants)
        for p in participants:
            p['amount_paid'] = equal_amount
    else:
        return jsonify({"error": "Invalid split method"}), 400

    return jsonify({"message": "Expense split successfully"})


if __name__ == "__main__":
    app.run(debug=True)
