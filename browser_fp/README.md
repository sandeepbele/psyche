
Demo 

- user identification
: user logs in , he sees summary page .. last visit ..associated devices etc.

- bot detection 
: user logs in .. ok from normal browser .. error if logged in from bot

- credential stuffing detection 
: anomaly detection | aggregated traffic spike in login attempts / failed attempts -> area chart .. spike in failed login attempts overlayed with number of bot attempts and number of attempts where compromised credentilas were used. 

- Remote login detection 
: ???

- account creation score
: based on email analysis etc.

- multiple accounts 
: different user names sharing same devices 

- account sharing 
: same id ..multiple devices ..multiple timezones etc. 

demo/login
: first time: ask for email/password 
: second time: only ask for email 
: third time: put in different email -> ask for password as new device
: fourth time: ..improve on score ..associate device to account based on recent logins 

demo/amibot
: ask for email/password 
: if bot ..say request can't be processed ... contact support


** Look at https://evidence.dev/ for dashboarding


09/30/2023 09:13:35 AM(-07:00)
- js -> decode -> form -> evaluate_fp flow works 
- ..BUT localhost execution results in blocked (browser) workerscope ..need to deploy to a domain for further dev
- lets work on deployment .. 3 docker files / projects 
-  1: js/ts : strip js/ts code to necessities : build .. upload to CDN
-  2: host browserintel as API 
-  3: logindemo as another app : own database   


docker run -d --name enigma --network host -p 6000:8000 --env-file /home/prod/.env -v /home/prod/app/enigma:/app sandeepbele/fraudiq-enigma:latest