"""
config.py — Input Configuration for DBMS Project
=================================================
Define the reference schema and functional dependencies here.
Modify SCHEMA_STR and FD_STRINGS to test different relations.
"""

# Reference relation schema
SCHEMA_STR = "R(BookingID, CustomerID, Name, Phone, BikeID, Model, CategoryID, CategoryName, StartDate, EndDate, PaymentID, Amount)"

# Functional Dependencies as human-readable strings
FD_STRINGS = [
    "BookingID -> CustomerID, BikeID, StartDate, EndDate",
    "CustomerID -> Name, Phone",
    "BikeID -> Model, CategoryID",
    "CategoryID -> CategoryName",
    "PaymentID -> BookingID, Amount",
]
