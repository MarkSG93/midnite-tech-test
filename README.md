# Midnite Tech Test Readme

## Description

Repository for my Midnite Technical Test submission. The application was TDD’d and is written in Python3.x. The application consists of a single endpoint; `/event`. This endpoint accepts a JSON payload that should be structured in the following format: 

```json
{
	"type": "deposit", // event type
	"amount": "42.00", //currency amount of event 
	"user_id": 1, // id of the user
	"t": 10 //second the payload was received
}
```

Upon a successful request you will receive a response that is a 200 OK with a payload structured as:

```json
{
  "alert": false,
  "alert_codes": [],
  "user_id": 1
}
```

If the event triggered any alerts, the payload you receive will include the associated alert codes and set the `alert` property to true.

The endpoint *only* accepts event types of either `deposit` or `withdrawal`.

## Install dependencies

It is recommended to create a `venv` before installing the dependencies. 

To install dependencies run `pip install -r requirements.txt`

## Run the app

This is a python 3 application so it must be run using python version 3

`python app.py`  or `python3 app.py` depending on your machine setup.

Make a request: 
`curl -XPOST http://127.0.0.1:5000/event -H 'Content-Type: application/json' \
-d '{"type": "deposit", "amount": "42.00", "user_id": 1, "t": 0}'`

## Run the tests

`pytest` - pretty easy!

## Assumptions and Cut Corners

### t value

The `t` value for the request payload is very odd. It doesn’t make sense to me that a system is receiving a single integer value to denote the *second* at which the payload was received. I assumed it was for simplicity in the technical test, however the simplicity created many more questions than answers and I concluded it doesn’t reflect real world systems. As a result, I used ISO formatted date strings as the stored data type that is the `now()` time of the system and then replacing the seconds of that time with the value received in the payload. 

### Payload validation

The brief didn’t mention anything of validation so I omitted 99% of it. The only validation that exists is on the received event type; the reason for this is I TDD’d the exercise and it was the first test I wrote and decided to keep it in. 

### Database

The database is hardly a well thought out and structured data structure (or even code implementation). As the exercise was only a few hours long I focused on the business logic of the requirements rather than database schemas and repository implementations of said database. It is a dictionary that contains keys that are accessed via an index throughout the code; which assumes that the value of the index is a row in the table. Ideally the database implementation would be an interface rather than directly manipulating the dictionary.

### Dodgy Dependency Injection

Usually I use factories to create objects as it allows me to inject dependencies into it during tests and deployment. However, this was my first time using Flask at all and Python in a few years so instead I opted for functions I can fake on the Flask `app` object. These two being to fake the database and also to provide a fake clock.

### Deployability

Because it's run via a python command, the application is not production ready. Usually I'd deploy APIs to Lambda and API Gateway but that was far too extreme for the exercise. I could have also created a dockerfile to build an image to run the application but it would effectively be the same as running `python app.py` on your own machine as I have assumed you already have Python installed.