# app/routes/customer_routes.py
from flask import Blueprint, render_template, request, redirect, url_for
from ..utils.db_utils import with_db

bp = Blueprint('customer', __name__)

@bp.route('/')
@with_db
def index(db):
    customers = db.execute(
        'SELECT * FROM customer ORDER BY name'
    ).fetchall()
    return render_template('customer_list.html', customers=customers)

@bp.route('/add', methods=['GET', 'POST'])
@with_db
def add_customer(db):
    if request.method == 'POST':
        db.execute(
            'INSERT INTO customer (name, email, phone, street, city, postal_code, '
            'country, vat_number, payment_terms, notes)'
            ' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (request.form['name'], request.form['email'], request.form['phone'],
             request.form['street'], request.form['city'], request.form['postal_code'],
             request.form['country'], request.form['vat_number'], 
             request.form['payment_terms'], request.form['notes'])
        )
        db.commit()
        return redirect(url_for('customer.index'))
    return render_template('customer_form.html')

@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@with_db
def edit_customer(db, id):
    if request.method == 'POST':
        db.execute(
            'UPDATE customer SET name=?, email=?, phone=?, street=?, city=?, '
            'postal_code=?, country=?, vat_number=?, payment_terms=?, notes=? '
            'WHERE id=?',
            (request.form['name'], request.form['email'], request.form['phone'],
             request.form['street'], request.form['city'], request.form['postal_code'],
             request.form['country'], request.form['vat_number'],
             request.form['payment_terms'], request.form['notes'], id)
        )
        db.commit()
        return redirect(url_for('customer.index'))
        
    customer = db.execute('SELECT * FROM customer WHERE id = ?', [id]).fetchone()
    return render_template('customer_form.html', customer=customer)

@bp.route('/<int:id>/delete', methods=['POST'])
@with_db
def delete_customer(db, id):
    db.execute('DELETE FROM customer WHERE id = ?', [id])
    db.commit()
    return redirect(url_for('customer.index'))