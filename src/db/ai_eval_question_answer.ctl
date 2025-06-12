load data
infile 'supportagents.csv'
into table supportagents
fields terminated by "," optionally enclosed by '"'
( question,answer )
