## Installation

Requirements:
- Miniconda 3 (install it from [here](https://docs.anaconda.com/miniconda/miniconda-install/))

**OR**

- Docker (easier)

### Docker
First you have to build the image using:

```bash
docker build . -t restormerui-backend
```

> 🛈 NOTE: Building the image might take a lot of time if you have a slower internet connection

Then run the backend using:

```bash
docker run -dp 8000:8000 \
    -v ./db.sqlite:/app/db.sqlite \
    -e SECRET=$(openssl rand -hex 32) \
    -e S3_BUCKET="your bucket" \ # this is optional
    -e ENVIRONMENT="PRODUCTION" \ # leave blank to see the api docs
    --name=restormerui-backend \
    restormerui-backend:latest
```

The application will run on 8000 port on localhost.

To get the `username` and `password`, run this command:
```bash
docker logs restormerui-backend | grep token
````
## Miniconda

> Installing using Miniconda is a bit difficult and not recommended unless you plan to develop the app further

**1. Create a new environment with Python 3.7:**

```
conda create -n restormerui-backend python=3.7
```

**2. Activate the environment and install pytorch**

```
conda activate restormerui-backend
conda install pytorch=1.8 torchvision torchaudio cpuonly -c pytorch -y
```

**3. Install requirements**

```
pip install -r requirements.txt
```

**4. Run your application**

Copy sample.env to your .env

```
cp sample.env .env
```

Make sure to make the necessary changes in the .env file before proceeding

In the root directory of this project run this:

```
uvicorn main:app # --reload --port <PORT> if running in dev environment
```
