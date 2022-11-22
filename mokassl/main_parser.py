import logging
import os
import random
import re

from flask import Flask, jsonify, request
from flask_cors import CORS

import environment.env
from commons.functions import get_moka_as_dict
from commons.functions import is_moka_allowed
from commons.functions import record_request
from commons.mockers import rand_floating
from commons.mockers import rand_int
from commons.mockers import rand_string
from commons.mockers import types_generator


def parse_model(schema: dict, schemas: dict, property_name: str = None, printLog=True):
    if printLog:
        print('Parsing schema:')
        print(schema)

    # We are in a similar case:
    #
    #     components:
    #       schemas:
    #         AnyValue: {}
    if len(schema.keys()) <= 0:
        return types_generator['string']['default']()

    if 'oneOf' in schema:
        return parse_model(schema['oneOf'][random.randint(0, len(schema['oneOf']) - 1)], schemas, printLog=False)

    if 'anyOf' in schema:
        selected = schema['anyOf'][random.randint(0, len(schema['anyOf']) - 1)]
        print('selected', selected)
        return parse_model(selected, schemas, printLog=False)

    if 'nullable' in schema and schema['nullable']:
        # todo: Prob(return null) = 0.2
        if random.random() > 0.8:
            return None

    if "$ref" in schema:
        key = schema["$ref"]
        if key[0] == '#':
            ref = schemas[key.split('/')[-1]]
            return parse_model(ref, schemas, printLog=False)
        else:
            # external ref not managed
            return {'not-managed': 'external ref not managed'}

    if schema['type'] == 'array':
        min_items = schema['minItems'] if 'minItems' in schema else 1
        max_items = schema['maxItems'] if 'maxItems' in schema else 5
        unique_items = schema['uniqueItems'] if 'uniqueItems' in schema else False
        ret = []
        for i in range(random.randint(min_items, max_items)):
            ret.append(parse_model(schema['items'], schemas, property_name=property_name, printLog=False))

        if unique_items:
            return set(ret)
        return ret

    if schema['type'] == 'object':
        ret = dict()
        properties = schema['properties'] if 'properties' in schema else []
        for p in properties:
            ret[p] = parse_model(properties[p], schemas, property_name=p, printLog=False)
        return ret

    if schema['type'] in types_generator:
        _type = schema['type']
        if 'enum' in schema:
            return schema['enum'][random.randint(0, len(schema['enum']) - 1)]

        if 'format' in schema:
            _format = schema['format']
        else:
            _format = 'default'

        if _type == 'integer':
            return rand_int(_format, schema)

        if _type == 'number':
            return rand_floating(_format, schema)

        if _type == 'string':
            return rand_string(_format, schema, property_name)

        return types_generator[_type][_format](property_name)

    return {}


def flask_handler(**kwargs):
    """
        **kwargs contains path-params
    """

    host_parts = request.host.split('.')
    # todo: uncomment
    if len(host_parts) != 3:
        return {'error': f'Cannot manage this host, too many parts: {request.host}'}, 400

    app_id = host_parts[-3]

    error, is_allowed = is_moka_allowed(app_id)

    if not is_allowed:
        return {'error': error, 'moka': f'{app_id}'}, 402

    moka, success = get_moka_as_dict(app_id)

    if not success:
        return {'error': f'Cannot find your moka: {app_id}'}, 404

    # global schemas
    schemas: dict = moka['schemas']
    paths = moka['paths']
    common_name = moka['commonName']

    if 'path' not in kwargs:
        return site_map(common_name, paths)

    req_path = '/' + kwargs['path']

    if req_path in ['/', '/site-map']:
        return site_map(common_name, paths)

    path = None
    print(f'looking for path matching: {req_path}')

    # Searching for 100% match
    for p in paths:
        if p == req_path:
            print('correct match found', p)
            path = p
            break

    if path is None:
        for p in paths:
            spliced = p.split("/")
            for i, s in enumerate(spliced):
                if re.search('{.*}', s):
                    spliced[i] = f"{re.sub('{.*}', '[^/]+', s)}"
            adapted_p = "^" + "/".join(spliced) + "$"

            # adapted_p = f"^{re.sub('{.*}', '[^/]+', p)}$"
            print(f"checking {p} adapted as {adapted_p}")
            if re.match(adapted_p, req_path) is not None:
                path = p
                break

    if path is None:
        return {'error': 'Route not found'}, 404

    print(f'Matched path: {path}')

    if request.method.lower() in paths[path]:
        responses = paths[path][request.method.lower()]['responses']
    elif request.method in paths[path]:
        responses = paths[path][request.method]['responses']
    else:
        return {'error': 'Method not found'}, 404

    # todo: handle body validation
    #     "/api/models/{code}/versions/{versionNumber}/{subversionNumber}/accounting-schema": {
    #       "put": {
    #         "tags": [
    #           "model-controller"
    #         ],
    #         "operationId": "setVersionAccountingSchema",
    #         "requestBody": {
    #           "content": {
    #             "application/json": {
    #               "schema": {
    #                 "type": "string"
    #               }
    #             }
    #           }
    #         },
    #         "responses": {
    #           "200": {
    #             "description": "default response"
    #           }
    #         },
    #         "security": [
    #           {
    #             "bearer-key": []
    #           }
    #         ]
    #       }
    #     },

    if '200' in responses:
        content = responses['200']['content']
    elif 'default' in responses:
        content = responses['default']['content']
    else:
        return {'error': 'No response type'}, 404

    # TODO manage Accept request header
    # accept = request.headers['accept']
    #
    # if accept in content:
    #     schema = content[accept]['schema']
    # elif '*/*' in content:
    #     schema = content['*/*']['schema']
    # else:
    #     return {'error': 'Cannot manage content-type'}, 400

    if '*/*' in content:
        schema = content['*/*']['schema']
    else:
        first_content = list(content.keys())[0]
        schema = content[first_content]['schema']

    generated = parse_model(schema, schemas)

    record_request(app_id, request.method, path, request.remote_addr)

    return jsonify(generated)

    # return kwargs


def site_map(common_name, paths):
    p_simple = dict()
    i = 1000
    for p in paths:
        for m in paths[p]:
            if 'operationId' in paths[p][m]:
                p_simple[paths[p][m]['operationId']] = {'method': m, 'path': p}
            else:
                p_simple['noOperationId_' + str(i)] = {'method': m, 'path': p}
                i += 1

    return jsonify({common_name: p_simple})


if __name__ == '__main__':
    methods = ['GET', 'POST', 'PUT', 'PATCH', 'PATCH', 'DELETE']

    logging.info(f'Starting moka parser v.{environment.env.VERSION}')
    logging.info(f'DEBUG  v.{os.environ.get("TEST_ENV") }')
    app = Flask('moka_parser')
    CORS(app, resources={r"/*": {"origins": "*"}})
    app.config['CORS_HEADERS'] = 'Content-Type'

    app.add_url_rule('/<path:path>', methods=methods, view_func=flask_handler)
    app.add_url_rule('/', methods=methods, view_func=flask_handler)
    app.run(port=environment.env.PORT, host='0.0.0.0')

    # moka, success = get_moka('87c3070f-78ff-4a9c-adb2-377dad45006b')
    # print(parse_model({'$ref': '#/components/schemas/User'}, moka['schemas']))
