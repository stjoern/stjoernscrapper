# stjoernscrapper

Stjoern scrapper collects important statistical data related to the market prices.

## Getting Started

If you ever need help while using stjoernscrapper, you need to type:
```
python startscrap.py -h
```

### Prerequisites

You need to install Chromedriver.

### Installing

- [Python 2.7 or 3.0 required]
- [chromedriver](https://chromedriver.storage.googleapis.com/index.html?path=2.32/) currently supported only chromedriver 
- [mongoDB](https://www.mongodb.com/download-center?jmp=nav#atlas) install nosql database where data will be stored
- [R](https://cloud.r-project.org/) install R for statistical computing

You will need additionaly install libraries for python and R language.

:snake: in the **stjoernscrapper** folder:
```
pip install -r requirements.txt
```
**R language** - you will need to install *RMongo* package
you can install it either like:
```
install.packages("devtools")
library(devtools)
install_github("Rmongo")
```
or
```
install.packages("RMongo")
```

## Running the tests

You can start using stjoernscrapper as 'multithreaded' or 'singlethreaded' by defining in config.py the variable threading=True or False

### To feed the stjoernscrapper with websites to be scrapped, there is [www.txt](https://github.com/stjoern/stjoernscrapper/blob/master/www.txt) file containing URL with class name.

Stjoernscrapper has no GUI, it's console application.

```
python startscrap.py -i www.txt 
```
or in debug mode:
```
python startscrap.py -i www.txt -v
```

# Evaluate data in R Language:
```
library(RMongo)
db<-mongoDbConnect('stjoern-scrapper', 'localhost',27017)
query<-dbGetQuery(db,"itesco", "{'title':'Banany', 'price': {'$gt': 20}}")
data<-query[c('price','sortiment','ts')]
summary(data)
dbDisconnect(db)
```
**to insert some data:**
```
dbInsertDocument(db,"itesco",'{"title":"New article", "price": 0.0}')
```
**other commands:**
```
dbGetDistinct(db,'itesco','sortiment')
dbRemoveQuery(db,'itesco','{"sortiment":"ovoce a zelenina"}')
```

**Aggregation (pipeline mechanism):**
![alt text](https://docs.mongodb.com/manual/_images/aggregation-pipeline.bakedsvg.svg)
```
output<-dbAggregate(db,"itesco",c(' { "$match":{"status":"A"} }',
								  ' { "$group": {"_id": "$cust_id", "total": {"$sum": "$amount"}} } ))
print(output)
```

## Deployment

In your chosen directory type:
```
git clone https://github.com/stjoern/stjoernscrapper
git checkout master
git fetch --all
```

## Versioning

We use [Git](https://git-scm.com/) for versioning. For the versions available, see the [tags on this repository](https://github.com/stjoern/stjoernscrapper/tags). 

## Authors

* **Monika vos Mueller** - *Initial work* - [Stjoern](https://github.com/stjoern/)

See also the list of [contributors](https://github.com/stjoern/stjoernscrapper/graphs/contributors) who participated in this project.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments

* used by Komercni banka



