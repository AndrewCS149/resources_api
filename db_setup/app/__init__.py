import yaml
import time
from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import exc

from configs import Config

app = Flask(__name__)

app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

from .models import Resource, Category, Language


def import_resources():
    # Step 1: Get data
    with open('resources.yml', 'r') as f:
        data = yaml.load(f)

    # Step 2: Uniquify resources
    unique_resources = remove_duplicates(data) 

    # Step 3: Get existing entries from DB
    try:
        resources_list = Resource.query.all()
        languages_list = Language.query.all()
        categories_list = Category.query.all()

        # Convert to dict for quick lookup
        existing_resources = {r.url:r for r in resources_list}
        language_dict = {l.name: l for l in languages_list}
        category_dict = {c.name: c for c in categories_list}
    except Exception as e:
        print(e)

    # Step 4: Create/Update each resource in the DB
    for resource in unique_resources:
        category = get_category(resource, category_dict) # Note: modifies the category_dict in place (bad?)
        langs = get_languages(resource, language_dict) # Note: modifies the language_dict in place (bad?)
        existing_resource = existing_resources.get(resource['url'])

        if existing_resource:
            update_resource(resource, existing_resource, langs, category)
        else:
            create_resource(resource, langs, category)

def remove_duplicates(data):
    unique_resources = []
    resource_dict = {}
    for resource in data:
        if not resource_dict.get(resource['url']):
            resource_dict[resource['url']] = True
            unique_resources.append(resource)
    return unique_resources

def get_category(resource, category_dict):
    category = resource.get('category')

    if category not in category_dict:
        category_dict[category] = Category(name=category)

    return category_dict[category]

def get_languages(resource, language_dict):
    langs = []

    # Loop through languages and create a new Language
    # object for any that don't exist in the DB
    for language in resource.get('languages') or []:
        if language not in language_dict:
            language_dict[language] = Language(name=language)

        # Add each Language object associated with this resource
        # to the list we'll return
        langs.append(language_dict[language])

    return langs

def create_resource(resource, langs, category):
    try:
        new_resource = Resource(
            name=resource['name'],
            url=resource['url'],
            category=category,
            languages=langs,
            paid=resource.get('paid'),
            notes=resource.get('notes', ''),
            upvotes=resource.get('upvotes', 0),
            downvotes=resource.get('downvotes', 0),
            times_clicked=resource.get('times_clicked', 0))

        db.session.add(new_resource)
        db.session.commit()
    except exc.SQLAlchemyError as e:
        db.session.rollback()
        print('Flask SQLAlchemy Exception:', e)
        template = "An SQLAlchemy exception of type {0} occurred. Arguments:\n{1!r}"
        print(resource)
    except Exception as e:
        db.session.rollback()
        print('exception', e)
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        print(resource)

def update_resource(resource, existing_resource, langs, category):
    # Return without updating if the resource is already up to date
    if match_resource(resource, existing_resource, langs):
        return

    try:
        existing_resource.name = resource['name']
        existing_resource.url = resource['url']
        existing_resource.category = category
        existing_resource.paid = resource.get('paid')
        existing_resource.notes = resource.get('notes', '')
        existing_resource.languages = langs

        db.session.commit()
    except exc.SQLAlchemyError as e:
        db.session.rollback()
        print('Flask SQLAlchemy Exception:', e)
        template = "An SQLAlchemy exception of type {0} occurred. Arguments:\n{1!r}"
        print(resource)
    except Exception as e:
        db.session.rollback()
        print('exception', e)
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        print(resource)

def match_resource(resource_dict, resource_obj, langs):
    if resource_dict['name'] != resource_obj.name:
        return False
    if resource_dict['paid'] != resource_obj.paid:
        return False
    if resource_dict['notes'] != resource_obj.notes:
        return False
    if resource_dict['category'] != resource_obj.category.name:
        return False
    if langs != resource_obj.languages:
        return False
    return True

start = time.perf_counter()
import_resources()
stop = time.perf_counter()
print('we loaded boys')
print("Elapsed time: %.1f [min]" % ((stop-start)/60))

wait = input('did it work?')
