load data
infile 'supportagents.csv'
into table supportagents
fields terminated by "," optionally enclosed by '"'
( AgentID,FirstName,LastName,Email,Phone )
