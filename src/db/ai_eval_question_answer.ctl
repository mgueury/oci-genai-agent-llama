load data
infile 'ai_eval_question_answer.csv'
into table AI_EVAL_QUESTION_ANSWER
fields terminated by "," optionally enclosed by '"'
( 
  question CHAR(20000),
  answer CHAR(20000)
)
