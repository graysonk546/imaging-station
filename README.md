# imaging-station
Codebase for a fastener imaging station.


# How to refresh the rclone token
We use rclone to copy our imaging tests to google drive.
It uses a token to upload to drive that expires pretty often (like daily?)

From command line, run
```
rclone config
```
Type `e` to select the `edit existing remote` option

Choose the `gdrive` option

We don't want to edit anything, so just keep pressing "enter" to select all the default options.

At some point, this option appears in terminal:
```
Already have a token - refresh?
y) Yes (default)
n) No
```
Press "enter" to select the default. Press "enter" again to use the autoconfig.

A google account webpage will appear. Choose the screwsorter459@gmail.com account.
Disregard the warning and hit continue till you get "Success!"

Return to the terminal, it should show "Got code". Press enter again until you return to the main menu, then you can type `q` to exit.

You can verify the token works by typing
```
rclone lsd gdrive:2306\ Screw\ Sorter
```

It should list the top-level directories in our screw sorter folder.
