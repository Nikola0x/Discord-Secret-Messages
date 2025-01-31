# Discord-Secret-Messages
This discord bot allows you to view, add, delete messages in private without anyone being able to see the messages

Basicly it uses API to send data to the backend, checks if the users is authenticated, if the users is authenticated it send the data to the users dm. Remember to allow messages in DM's from bots for this to work.
If user tried to use the command without the permission he will be hit with a erorr message. 
The program should be secure i will continue to do some updates to ensure this is secure, fast and has a lot of features

How to use the bot
First download the files, Unzip them. Open the file Backend and create a file name ".env" in which you will put the following data
```
DISCORD_TOKEN=
OWNER_ID=
API_KEY=
```
Change the DISCORD_TOKEN to the bots token
OWNER_ID to the user that has permission to do everything
API_KEY this is the key that you must remember/save and it is the secret that allows you to connect to the server (best practise is to slam random keys so this is secure as possible)
After that open your host where you will host the backend, do the followind command one by one
```
pip install -r requirements.txt
python main.py
```
and the bot should give you the message that it is up.

After you have done that open the other folder name "Frontend" and open the file named client.py. Change the line 29 in which you need to change the api_url so this is used to communicate with your server. If your server host IP is 178.95.208.84 , if you are localhosting it just enter " localhost"  and leave the port to 8000 since that is the default port of the program. After that just save the file, open it and it will open a user interface. In here you need to input your discord ID and the API key from the .env file that you configurated before. If you want you can click the button to save the data so you dont need to do this again. And then click connect.
The server will let you know that you are connected after that you can go on your server and do some of the following command

```
!viewadd
!view
!viewdelete
```
Viewadd adds a message to the database, you can also add categories
view sends you a dm with all the messages that you made
viewdelete allows you to delete the message you need to have the randomised key that the message uses.
