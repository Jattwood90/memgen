To start

```bash
cd python
```

### Run the app

To run the app, run the following command:

```bash
./run
```

This will run `docker compose` in daemon mode, to build and start all app
services. It may take several minutes for the app to build and start the first
time.

### Access the app

If running locally, the app will be available at [http://localhost:10114]()
GitHub Codespaces and GitPod will will be available at the URL provided in the
terminal by the run script. You can also go to the Ports tab inside GitHub
Codespaces or GitPod to access the app which will be running on port 10114.

### Making changes

After making changes to a service, you can rebuild just that service by running:

```bash
./run [ backend-for-frontend | image-picker | meminator | phrase-picker ]
```

### Stop the app

```bash
./stop
```
