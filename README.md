# imaging-station
Codebase for a fastener imaging station.

# How to run the UI
Go to this directory
```
cd sw
```
Run the UI python script
```
./data_collection_backend.py
```


# How to refresh the rclone token
We use rclone to copy our imaging tests to google drive. You can read more about it [here](https://rclone.org/drive/).
It uses a token to upload to drive that expires pretty often (like daily?)

Open command line (Ctrl + Alt + T on the Imaging Station) and type the following:
```
rclone config reconnect gdrive_more_storage:
```
This will appear:
```
Already have a token - refresh?
y) Yes (default)
n) No
```
Type "y" and press "enter". Then this will appear next:
```
Use web browser to automatically authenticate rclone with remote?
 * Say Y if the machine running rclone has a web browser you can use
 * Say N if running rclone on a (remote) machine without web browser access
If not sure try Y. If Y failed, try N.

y) Yes (default)
n) No
y/n>
```
Respond with "y" again.

Your web browser should launch and direct you to sign in. Login to screw.sorter.2357@gmail.com, the credentials should already be saved in the browser.

After logging in, you'll see a scary screen saying "Google hasn't verified this app". Disregard that, the app was created by us to upload files to google drive. Click "advanced" -> "Go to rclone screw sorter (unsafe)".

Then click "Continue" and you should see a white screen with "Success!" at top.

If you return to your command line, you'll see the following:
```
2023/11/20 23:45:01 NOTICE: Make sure your Redirect URL is set to "http://127.0.0.1:53682/" in your custom config.
2023/11/20 23:45:01 NOTICE: If your browser doesn't open automatically go to the following link: http://127.0.0.1:53682/auth?state=lZ7vYKchroHJGHz_3vuNNw
2023/11/20 23:45:01 NOTICE: Log in and authorize rclone for access
2023/11/20 23:45:01 NOTICE: Waiting for code...
2023/11/20 23:47:18 NOTICE: Got code
Configure this as a Shared Drive (Team Drive)?

y) Yes
n) No (default)
y/n>
```

Respond with "n".

You can verify the token works by typing into your command line.
```
rclone lsd gdrive_more_storage:2357\ Screw\ Sorter
```

It should list the top-level directories in our screw sorter folder.
