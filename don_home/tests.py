from django.test import TestCase
from sqlalchemy import create_engine

# Create your tests here.
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.sql import text

engine = create_engine('mysql+pymysql://root:&donone1!K&@donone-db.cyfp8pevwfx6.ap-northeast-1.rds.amazonaws.com:3306/dononedb')

Session = scoped_session(sessionmaker(bind=engine))

SQL = """
SELECT 
    DATE_FORMAT(`주문일자`,'%Y-%m') date
    ,SUM(판매가) 
FROM don_home_unionorder
WHERE (`주문일자` >= date_add(now(), interval -1 YEAR))
GROUP BY date
ORDER BY date;
"""


s = Session()
q = []
a = []
result = s.execute(text(SQL)).all()
for i in result:
    q.append(i[0])
    print(i)

print(q)
print(a)

engine.dispose()