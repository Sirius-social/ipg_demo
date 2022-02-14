import os
import logging
import argparse
from datetime import datetime

import uvicorn
import sirius_sdk
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import settings
from app.settings import URL_STATIC
from operations import create_identity


app = FastAPI()
app.mount(URL_STATIC, StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


STATIC_CFG = {
    'styles': URL_STATIC + '/admin/css/styles.css',
    'vue': URL_STATIC + '/vue.min.js',
    'axios': URL_STATIC + '/axios.min.js',
    'jquery': URL_STATIC + '/jquery-3.6.0.min.js'
}


@app.get("/actor1")
async def index(request: Request):
    context = {
        'static': STATIC_CFG,
        'title': 'Company Ltd.'
    }
    async with sirius_sdk.context(**settings.ACTOR1):
        pass
    response = templates.TemplateResponse(
        "cabinet.html",
        {
            "request": request,
            **context
        }
    )
    return response


@app.get("/health_check")
async def health_check():
    return {"utc": datetime.utcnow().isoformat()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--production', choices=['on', 'yes'], required=False)
    args = parser.parse_args()
    is_production = args.production is not None
    args = ()
    kwargs = {}
    if is_production:
        logging.warning('\n')
        logging.warning('\t*************************************')
        logging.warning('\tApplication will be run in PRODUCTION mode')
        logging.warning('\t*************************************')
        args = ['app.main:app']
        kwargs['proxy_headers'] = True
        uvicorn.run(*args, host="0.0.0.0", port=80, workers=int(os.getenv('WORKERS')), **kwargs)
    else:
        logging.warning('\n')
        logging.warning('\t*************************************')
        logging.warning('\tApplication will be run in DEBUG mode')
        logging.warning('\t*************************************')
        uvicorn.run(app, host="0.0.0.0", port=80, **kwargs)
