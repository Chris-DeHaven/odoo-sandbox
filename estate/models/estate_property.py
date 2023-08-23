from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
import math
import calendar
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta


class EstateProperty(models.Model):
    _name = "estate.property"
    _description = "Estate Property"
    _order = "name desc"

    def cancel_property(self):
        for record in self:
            if record.state == "sold":
                raise UserError("Sold properties cannot be canceled.")
            else:
                record.state = "canceled"

    def sold_property(self):
        for record in self:
            if record.state == "canceled":
                raise UserError("Canceled properties cannot be sold.")
        else:
            record.state = "sold"

    name = fields.Char(" ", required=True, translate=True, default="New")
    description = fields.Text("Description", required=True)
    postcode = fields.Char("Postcode", required=True)
    date_availability = fields.Date(
        "Available From",
        copy=False,
        default=(date.today() + relativedelta(months=3)),
        required=True,
    )
    expected_price = fields.Float("Expected Price")
    selling_price = fields.Float("Selling Price", readonly=True, copy=False)
    bedrooms = fields.Integer("Bedrooms", required=True, default="2")
    living_area = fields.Integer("Living Area (sqm)", required=True)
    facades = fields.Integer("Facades")
    garage = fields.Boolean("Garage")
    garden = fields.Boolean("Garden")
    garden_area = fields.Integer("Garden Area (sqm)", required=True)
    garden_orientation = fields.Selection(
        string="Garden Orientation",
        selection=[
            ("north", "North"),
            ("south", "South"),
            ("east", "East"),
            ("west", "West"),
        ],
    )
    active = fields.Boolean("Active", default=True)
    state = fields.Selection(
        string="State",
        selection=[
            ("new", "New"),
            ("offer_received", "Offer Received"),
            ("offer_accepted", "Offer Accepted"),
            ("sold", "Sold"),
            ("canceled", "Canceled"),
        ],
        default="new",
    )
    property_type_id = fields.Many2one("estate.property.type", string="Property Type")
    seller = fields.Many2one(
        "res.users", string="Salesman", default=lambda self: self.env.user
    )
    buyer = fields.Many2one("res.partner", string="Buyer", copy=False)
    tag_ids = fields.Many2many("estate.property.tag", string="Tags")
    offer_ids = fields.One2many("estate.property.offer", "property_id", string="Offers")
    total_area = fields.Float(compute="_compute_total_area")
    best_price = fields.Float(compute="_compute_best_price", string="Best Price")

    @api.depends("offer_ids.price")
    def _compute_best_price(self):
        for property in self:
            if property.offer_ids:
                alloffers = property.offer_ids.mapped("price")
                property.best_price = max(alloffers)
                # for offer in property.offer_ids:
                #     current_best_price = offer.price
                #     if (current_best_price > property.best_price):
                #         property.best_price = current_best_price
            else:
                property.best_price = 0

    @api.depends("living_area", "garden_area")
    def _compute_total_area(self):
        for record in self:
            record.total_area = record.living_area + record.garden_area

    @api.onchange("garden")
    def _onchange_garden(self):
        if self.garden == True:
            self.garden_area = 10
            self.garden_orientation = "north"
        else:
            self.garden_area = 0
            self.garden_orientation = ""

    @api.constrains("expected_price", "selling_price")
    def _ensure_proper_price(self):
        for property in self:
            if (property.state == "offer_accepted") and (
                property.selling_price < property.expected_price * 0.9
            ):
                raise ValidationError(
                    "The selling price must be at least 90% of the expected price! You must reduce the expected price if you want to accept this offer."
                )

    _sql_constraints = [
        (
            "check_expected_price",
            "CHECK(expected_price >= 0)",
            "The expected price must be strictly positive",
        ),
        (
            "check_selling_price",
            "CHECK(selling_price >= 0)",
            "The selling price must be positive",
        ),
    ]


class PropertyType(models.Model):
    _name = "estate.property.type"
    _description = "Property Type"
    _order = "name"

    name = fields.Char("name", required=True)
    property_ids = fields.One2many("estate.property", "property_type_id")
    sequence= fields.Integer('Sequence', default= 1)
    offer_ids= fields.One2many("estate.property.offer", inverse_name= "property_type_id")
    offer_count= fields.Integer(compute="_compute_count")

    _sql_constraints = [
        ("check_unique_type", "UNIQUE(name)", "The name must be unique")
    ]

    @api.depends("offer_ids")
    def _compute_count(self):
        for record in self:
            record.offer_count= len(record.offer_ids)


class PropertyTag(models.Model):
    _name = "estate.property.tag"
    _description = "Property Tag"
    _order = "name"

    name = fields.Char("name", required=True)
    color= fields.Integer("Color")

    _sql_constraints = [("check_unique_tag", "UNIQUE(name)", "The tag must be unique")]


class EstateOffer(models.Model):
    _name = "estate.property.offer"
    _description = "Estate Offer"
    _order = "price desc"

    def accept_offer(self):
        for offer in self:
            offer.status = "accepted"
            offer.property_id.selling_price = offer.price
            offer.property_id.state= "offer_accepted"
            for other_offer in offer.property_id.offer_ids:
                if other_offer != offer:
                    other_offer.refuse_offer()
            offer.property_id.buyer = offer.partner_id

    def refuse_offer(self):
        for offer in self:
            offer.status = "refused"

    price = fields.Float("Price")
    status = fields.Selection(
        string="Status",
        selection=[("accepted", "Accepted"), ("refused", "Refused")],
        copy=False,
    )
    partner_id = fields.Many2one("res.partner", string="Partner", required=True)
    property_id = fields.Many2one("estate.property", required=True)
    property_type_id= fields.Many2one("estate.property.type", related= "property_id.property_type_id", store=True)
    validity = fields.Integer("Validity (days)", default=7)
    date_deadline = fields.Date(
        "Deadline", compute="_compute_deadline", inverse="_inverse_deadline"
    )

    @api.depends("validity")
    def _compute_deadline(self):
        for record in self:
            record.create_date = date.today()
            record.date_deadline = record.create_date + relativedelta(
                days=record.validity
            )

    def _inverse_deadline(self):
        for record in self:
            record.create_date = date.today()
            record.create_date = record.date_deadline - relativedelta(
                days=record.validity
            )

    _sql_constraints = [
        (
            "check_offer_price",
            "CHECK(price >= 0)",
            "An offer price must be strictly positive",
        )
    ]
