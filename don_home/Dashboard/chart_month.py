from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.sql import text

import pandas as pd
from cp2_don.don_settings import MYSQL_CONN
import numpy as np


def Chart_pre_month():
    engine = create_engine(MYSQL_CONN)
    conn = engine.raw_connection()
    Session = scoped_session(sessionmaker(bind=engine))
    s = Session()

    MONTH_OR = """
        SELECT 
            DATE_FORMAT(`주문일자`,'%Y-%m') date
            ,CAST(SUM(판매가) as SIGNED)
        FROM don_home_unionorder
        WHERE (`주문일자` >= date_add(now(), interval -1 YEAR))
        GROUP BY date
        ORDER BY date;
        """
    to_mon = []
    to_data_t = []
    to_mn = s.execute(text(MONTH_OR))
    for to in to_mn:
        to_mon.append(to[0])
        to_data_t.append(to[1])


    SQL1 = """
        SELECT 
            DATE_FORMAT(`주문일자`,'%Y-%m') date
            ,CAST(SUM(판매가) as SIGNED) as total
        FROM don_home_unionorder
        WHERE (`주문일자` >= date_add(now(), interval -1 YEAR))
        GROUP BY date
        ORDER BY date;
        """

    to_data = pd.read_sql(SQL1, conn)
    # ably
    SQL_AB = """
    SELECT 
        DATE_FORMAT(`주문일자`,'%Y-%m') date
        ,CAST(SUM(판매가) as SIGNED) as total
    FROM don_home_unionorder
    WHERE (`주문일자` >= date_add(now(), interval -1 YEAR))
    GROUP BY date, Platform 
    HAVING Platform = 'ABLY'
    ORDER BY date;
    """
    abdata = pd.read_sql(SQL_AB, conn)
    ab = pd.merge(to_data['date'], abdata, how='left')
    ab = ab.fillna(0)
    ab['total'] = ab['total'].astype(int)
    
    ab_data = list(np.array(ab['total'].tolist()))
    ab_mon = list(np.array(ab['date'].tolist()))

    # cafe24
    SQL_CF = """
    SELECT 
        DATE_FORMAT(`주문일자`,'%Y-%m') date
        ,CAST(SUM(판매가) as SIGNED) as total
    FROM don_home_unionorder
    WHERE (`주문일자` >= date_add(now(), interval -1 YEAR))
    GROUP BY date, Platform 
    HAVING Platform = 'Homepage'
    ORDER BY date;
    """
    cfdata = pd.read_sql(SQL_CF, conn)
    cf = pd.merge(to_data['date'], cfdata, how='left')
    cf = cf.fillna(0)
    cf['total'] = cf['total'].astype(int)
    
    cf_data = list(np.array(cf['total'].tolist()))
    cf_mon = list(np.array(cf['date'].tolist()))

    # naver
    SQL_NA = """
    SELECT 
        DATE_FORMAT(`주문일자`,'%Y-%m') date
        ,CAST(SUM(판매가) as SIGNED) as total
    FROM don_home_unionorder
    WHERE (`주문일자` >= date_add(now(), interval -1 YEAR))
    GROUP BY date, Platform 
    HAVING Platform = '스마트스토어'
    ORDER BY date;
    """
    nadata = pd.read_sql(SQL_NA, conn)
    na = pd.merge(to_data['date'], nadata, how='left')
    na = na.fillna(0)
    na['total'] = na['total'].astype(int)
    
    na_data = list(np.array(na['total'].tolist()))
    na_mon = list(np.array(na['date'].tolist()))
    

    conn.close()
    engine.dispose()

    return to_mon, to_data_t, ab_data, ab_mon, cf_data, cf_mon, na_data, na_mon

def Product_re_month():
    engine = create_engine(MYSQL_CONN)
    conn = engine.raw_connection()
    Session = scoped_session(sessionmaker(bind=engine))
    s = Session()

    mtore = []
    mabre = []
    mcfre = []
    mnare = []

    RE1 = """
    SELECT COUNT(`취소/반품`)
    FROM don_home_unionorder dhu 
    WHERE (`주문일자` >= date_add(now(), interval -1 MONTH))
    GROUP BY `취소/반품`
    HAVING `취소/반품` = 'T';
    """
    to_re = s.execute(text(RE1))
    for to in to_re:
        mtore.append(to[0])

    RE2 = """
    SELECT COUNT(`취소/반품`) AS `취소/반품 건수` FROM don_home_unionorder
    WHERE (`주문일자` >= date_add(now(), interval -1 MONTH))
    GROUP BY Platform, `취소/반품`
    HAVING `취소/반품` = 'T' AND Platform = 'ABLY';
    """
    ab_re = s.execute(text(RE2))
    for to in ab_re:
        mabre.append(to[0])

    RE3 = """
    SELECT COUNT(`취소/반품`) AS `취소/반품 건수` FROM don_home_unionorder
    WHERE (`주문일자` >= date_add(now(), interval -1 MONTH))
    GROUP BY Platform, `취소/반품`
    HAVING `취소/반품` = 'T' AND Platform = 'Homepage';
    """
    cf_re = s.execute(text(RE3))
    for to in cf_re:
        mcfre.append(to[0])

    RE4 = """
    SELECT COUNT(`취소/반품`) AS `취소/반품 건수` FROM don_home_unionorder
    WHERE (`주문일자` >= date_add(now(), interval -1 MONTH))
    GROUP BY Platform, `취소/반품`
    HAVING `취소/반품` = 'T' AND Platform = '스마트스토어';
    """
    na_re = s.execute(text(RE4))
    for to in na_re:
        mnare.append(to[0])

    conn.close()
    engine.dispose()

    return mnare, mcfre, mabre, mtore


def Product_total_month():
    engine = create_engine(MYSQL_CONN)
    conn = engine.raw_connection()

    # TOTAL
    SQL = """
    SELECT Platform, CAST(COUNT(Status) as SIGNED) as total
    FROM don_home_unionorder
    WHERE (`주문일자` >= date_add(now(), interval -1 MONTH))
    GROUP BY Platform;
    """
    to_pro_data = pd.read_sql(SQL, conn)
    to_pro_data = to_pro_data.replace('Homepage', 'Cafe24')

    tpn = list(np.array(to_pro_data['Platform'].tolist()))
    tpt = list(np.array(to_pro_data['total'].tolist()))

    # ABLY
    SQLAB = """
    SELECT Platform, 상품명 ,CAST(COUNT(수량) as SIGNED) as total
    FROM don_home_unionorder
    WHERE (`주문일자` >= date_add(now(), interval -1 MONTH))
    GROUP BY 상품명
    HAVING Platform = 'ABLY';
    """
    ab_pro_data = pd.read_sql(SQLAB, conn)

    apn = list(np.array(ab_pro_data['상품명'].tolist()))
    apt = list(np.array(ab_pro_data['total'].tolist()))

    # CAFE
    SQLCF = """
    SELECT Platform, 상품명 ,CAST(COUNT(수량) as SIGNED) as total
    FROM don_home_unionorder
    WHERE (`주문일자` >= date_add(now(), interval -1 MONTH))
    GROUP BY 상품명
    HAVING Platform = 'Homepage';
    """
    cf_pro_data = pd.read_sql(SQLCF, conn)

    cpn = list(np.array(cf_pro_data['상품명'].tolist()))
    cpt = list(np.array(cf_pro_data['total'].tolist()))

    # NAVER
    SQLNA = """
    SELECT Platform, 상품명 ,CAST(COUNT(수량) as SIGNED) as total
    FROM don_home_unionorder
    WHERE (`주문일자` >= date_add(now(), interval -1 MONTH))
    GROUP BY 상품명
    HAVING Platform = '스마트스토어';
    """
    na_pro_data = pd.read_sql(SQLNA, conn)

    npn = list(np.array(na_pro_data['상품명'].tolist()))
    npt = list(np.array(na_pro_data['total'].tolist()))

    conn.close()
    engine.dispose()

    return tpn, tpt, apn, apt, cpn, cpt, npn, npt



def total_order_month():
    engine = create_engine(MYSQL_CONN)
    conn = engine.raw_connection()
    Session = scoped_session(sessionmaker(bind=engine))
    s = Session()

    ORDER1 = """
    SELECT COUNT(Status) as total
    FROM don_home_unionorder
    WHERE (`주문일자` >= date_add(now(), interval -1 MONTH));
    """
    to_order = s.execute(text(ORDER1))
    for to in to_order:
        to_cou_order = to[0]

    ORDER2 = """
    SELECT COUNT(Status) as total
    FROM don_home_unionorder
    WHERE (`주문일자` >= date_add(now(), interval -1 MONTH))
    GROUP BY Platform 
    HAVING Platform = 'ABLY';
    """
    ab_order = s.execute(text(ORDER2))
    for to in ab_order:
        ab_cou_order = to[0]

    ORDER3 = """
    SELECT COUNT(Status) as total
    FROM don_home_unionorder
    WHERE (`주문일자` >= date_add(now(), interval -1 MONTH))
    GROUP BY Platform 
    HAVING Platform = 'ABLY';
    """
    cf_order = s.execute(text(ORDER3))
    for to in cf_order:
        cf_cou_order = to[0]

    ORDER4 = """
    SELECT COUNT(Status) as total
    FROM don_home_unionorder
    WHERE (`주문일자` >= date_add(now(), interval -1 MONTH))
    GROUP BY Platform 
    HAVING Platform = 'ABLY';
    """
    na_order = s.execute(text(ORDER4))
    for to in na_order:
        na_cou_order = to[0]

    conn.close()
    engine.dispose()

    return to_cou_order, ab_cou_order, cf_cou_order, na_cou_order


def total_sales_month():
    engine = create_engine(MYSQL_CONN)
    conn = engine.raw_connection()
    Session = scoped_session(sessionmaker(bind=engine))
    s = Session()

    SQL1 = """
    SELECT SUM(판매가)
    FROM don_home_unionorder dhu
    WHERE 주문일자 >= date_add(now(), interval -1 MONTH)
    """
    result = s.execute(text(SQL1))
    for re in result:
        result_t = re[0]

    SQL2 = """
    SELECT SUM(판매가)
    FROM don_home_unionorder dhu
    WHERE 주문일자 >= date_add(now(), interval -1 MONTH)
    GROUP BY Platform
    HAVING Platform = 'ABLY';
    """
    a_result = s.execute(text(SQL2))
    for re in a_result:
        ab_sales = re[0]

    SQL3 = """
    SELECT SUM(판매가)
    FROM don_home_unionorder dhu
    WHERE 주문일자 >= date_add(now(), interval -1 MONTH)
    GROUP BY Platform
    HAVING Platform = 'Homepage';
    """
    cf_result = s.execute(text(SQL3))
    for re in cf_result:
        cf_sales = re[0]

    SQL4 = """
    SELECT SUM(판매가)
    FROM don_home_unionorder dhu
    WHERE 주문일자 >= date_add(now(), interval -1 MONTH)
    GROUP BY Platform
    HAVING Platform = '스마트스토어';
    """
    na_result = s.execute(text(SQL4))
    for re in na_result:
        na_sales = re[0]

    conn.close()
    engine.dispose()

    return result_t, ab_sales, cf_sales, na_sales


def detail_order_month():
    engine = create_engine(MYSQL_CONN)
    conn = engine.raw_connection()
    Session = scoped_session(sessionmaker(bind=engine))
    s = Session()

    SQL_DE = """
    SELECT Platform, `주문번호`, Status, `주문일자`, `고객명`, `상품명`, `수량`, `판매가`, Profit 
    FROM don_home_unionorder
    WHERE (`주문일자` >= date_add(now(), interval -1 MONTH))
    ORDER BY `주문일자` DESC;
    """
    to_d = s.execute(text(SQL_DE))
    SQL_DE_AB = """
    SELECT Platform, `주문번호`, Status, `주문일자`, `고객명`, `상품명`, `수량`, `판매가`, Profit
    FROM don_home_unionorder
    WHERE (`주문일자` >= date_add(now(), interval -1 MONTH))
    HAVING Platform = 'ABLY';
    """
    ab_d = s.execute(text(SQL_DE_AB))
    SQL_DE_CF = """
    SELECT Platform, `주문번호`, Status, `주문일자`, `고객명`, `상품명`, `수량`, `판매가`, Profit
    FROM don_home_unionorder
    WHERE (`주문일자` >= date_add(now(), interval -1 MONTH))
    HAVING Platform = 'Homepage';
    """
    cf_d = s.execute(text(SQL_DE_CF))
    SQL_DE_NA = """
    SELECT Platform, `주문번호`, Status, `주문일자`, `고객명`, `상품명`, `수량`, `판매가`, Profit
    FROM don_home_unionorder
    WHERE (`주문일자` >= date_add(now(), interval -1 MONTH))
    HAVING Platform = '스마트스토어';
    """
    na_d = s.execute(text(SQL_DE_NA))

    conn.close()
    engine.dispose()

    return to_d, ab_d, cf_d, na_d