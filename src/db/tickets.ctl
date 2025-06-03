load data
infile 'tickets.csv'
into table tickets
fields terminated by "," optionally enclosed by '"'
( TicketID,
  CustomerName,
  Subject,
  Description CHAR(20000),
  CreatedDate,
  LastUpdatedDate,
  StatusID,
  AssignedToAgentID 
)
