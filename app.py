# -*- coding: utf-8 -*-
"""
负成本持仓策略Web应用 - Render兼容版
包含所有核心功能
"""

import os
import sqlite3
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import json
import math

app = Flask(__name__)
app.secret_key = 'strategy_management_2025_render'

# 数据库路径 - Render兼容
DB_DIR = os.environ.get('RENDER_EXTERNAL_VOLUME', os.path.join(os.path.dirname(__file__), 'data'))
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, 'strategy.db')

class StrategyDatabase:
    """策略数据库管理类"""
    
    def __init__(self):
        self.init_database()
    
    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 创建股票基本信息表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                market TEXT NOT NULL,
                target_shares INTEGER DEFAULT 100,
                initial_investment REAL DEFAULT 0,
                current_shares INTEGER DEFAULT 0,
                avg_cost REAL DEFAULT 0,
                total_fees REAL DEFAULT 0,
                current_price REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建交易记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_code TEXT NOT NULL,
                trade_type TEXT NOT NULL,
                shares INTEGER NOT NULL,
                price REAL NOT NULL,
                fees REAL DEFAULT 0,
                trade_date DATE NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (stock_code) REFERENCES stocks (code)
            )
        """)
        
        # 创建资金管理表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fund_management (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                total_capital REAL DEFAULT 0,
                available_funds REAL DEFAULT 0,
                invested_amount REAL DEFAULT 0,
                profit_reinvest_ratio REAL DEFAULT 0.5,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 检查是否有初始资金记录
        cursor.execute("SELECT COUNT(*) FROM fund_management")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO fund_management (total_capital, available_funds, invested_amount, profit_reinvest_ratio)
                VALUES (10000, 10000, 0, 0.5)
            """)
        
        conn.commit()
        conn.close()
    
    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(DB_PATH)

# 全局数据库实例
db = StrategyDatabase()

@app.route('/')
def index():
    """首页 - 持仓概览"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 获取所有股票
        cursor.execute("""
            SELECT id, code, name, market, target_shares, current_shares, 
                   avg_cost, current_price, initial_investment
            FROM stocks ORDER BY created_at DESC
        """)
        stocks = cursor.fetchall()
        
        # 获取资金信息
        cursor.execute("SELECT total_capital, available_funds, invested_amount FROM fund_management LIMIT 1")
        fund_data = cursor.fetchone() or (0, 0, 0)
        total_capital, available_funds, invested_amount = fund_data
        
        # 计算总体统计
        total_value = 0
        total_cost = 0
        total_profit = 0
        
        stock_list = []
        for stock in stocks:
            id, code, name, market, target_shares, current_shares, avg_cost, current_price, initial_investment = stock
            
            # 计算当前市值和盈亏
            current_value = current_shares * current_price
            total_cost_for_stock = current_shares * avg_cost
            profit = current_value - total_cost_for_stock
            profit_rate = (profit / total_cost_for_stock * 100) if total_cost_for_stock > 0 else 0
            
            # 计算负成本策略
            negative_cost_strategy = calculate_negative_cost_strategy(
                code, current_price, current_shares, avg_cost, target_shares
            )
            
            stock_data = {
                'id': id,
                'code': code,
                'name': name,
                'market': market,
                'target_shares': target_shares,
                'current_shares': current_shares,
                'avg_cost': avg_cost,
                'current_price': current_price,
                'current_value': current_value,
                'total_cost': total_cost_for_stock,
                'profit': profit,
                'profit_rate': profit_rate,
                'initial_investment': initial_investment,
                'strategy': negative_cost_strategy
            }
            
            stock_list.append(stock_data)
            total_value += current_value
            total_cost += total_cost_for_stock
            total_profit += profit
        
        total_profit_rate = (total_profit / total_cost * 100) if total_cost > 0 else 0
        
        conn.close()
        
        return render_template('index.html', 
                             stocks=stock_list,
                             total_value=total_value,
                             total_cost=total_cost,
                             total_profit=total_profit,
                             total_profit_rate=total_profit_rate,
                             total_capital=total_capital,
                             available_funds=available_funds,
                             invested_amount=invested_amount)
    
    except Exception as e:
        flash(f'数据加载错误: {str(e)}', 'error')
        return render_template('index.html', 
                             stocks=[],
                             total_value=0,
                             total_cost=0,
                             total_profit=0,
                             total_profit_rate=0,
                             total_capital=0,
                             available_funds=0,
                             invested_amount=0)

def calculate_negative_cost_strategy(code, current_price, current_shares, avg_cost, target_shares):
    """计算负成本策略"""
    try:
        # 基础计算
        current_value = current_shares * current_price
        total_cost = current_shares * avg_cost
        unrealized_profit = current_value - total_cost
        profit_rate = (unrealized_profit / total_cost * 100) if total_cost > 0 else 0
        
        # 持仓差距
        shares_gap = target_shares - current_shares
        
        # 负成本策略分析
        negative_cost_possible = False
        negative_cost_shares = 0
        negative_cost_proceeds = 0
        remaining_shares = current_shares
        remaining_cost = total_cost
        
        if unrealized_profit > 0 and current_shares > 0:
            # 计算可以卖出多少股实现负成本
            for shares_to_sell in range(1, current_shares):
                sell_value = shares_to_sell * current_price
                new_remaining_shares = current_shares - shares_to_sell
                new_remaining_cost = total_cost - sell_value
                
                if new_remaining_cost <= 0:
                    negative_cost_possible = True
                    negative_cost_shares = shares_to_sell
                    negative_cost_proceeds = abs(new_remaining_cost)
                    remaining_shares = new_remaining_shares
                    remaining_cost = 0
                    break
        
        # 投资建议
        if negative_cost_possible:
            action = "部分获利了结"
            suggestion = f"卖出{negative_cost_shares}股，剩余{remaining_shares}股成本为0"
            color = "success"
        elif profit_rate > 20:
            action = "考虑部分获利"
            suggestion = f"已盈利{profit_rate:.1f}%，可考虑卖出部分获利"
            color = "success"
        elif profit_rate < -10:
            action = "考虑逢低加仓"
            suggestion = f"已亏损{abs(profit_rate):.1f}%，可考虑低价加仓降低成本"
            color = "danger"
        elif shares_gap > 0:
            action = "继续建仓"
            suggestion = f"距离目标还差{shares_gap}股，可分批买入"
            color = "primary"
        else:
            action = "持有观望"
            suggestion = "当前持仓合理，继续观察市场"
            color = "info"
        
        # 风险评估
        volatility_risk = "高" if abs(profit_rate) > 15 else "中" if abs(profit_rate) > 5 else "低"
        position_risk = "高" if current_shares > target_shares * 1.2 else "中" if current_shares > target_shares * 0.8 else "低"
        
        # 波段操作建议
        if profit_rate > 15:
            band_advice = "波段高位，考虑减仓"
            band_detail = f"当前位置处于波段高位，可考虑减持{max(int(current_shares * 0.2), 1)}股锁定利润"
            band_profit_estimate = current_price * max(int(current_shares * 0.2), 1)
        elif profit_rate < -10:
            band_advice = "波段低位，考虑加仓"
            band_detail = f"当前位置处于波段低位，可考虑加仓{max(int(target_shares * 0.1), 1)}股降低成本"
            band_profit_estimate = 0
        else:
            band_advice = "波段中位，持有观望"
            band_detail = "当前位置处于波段中位，持有观望，等待更好买卖点"
            band_profit_estimate = 0
        
        # 资金管理建议
        if shares_gap > 0:
            funds_needed = shares_gap * current_price
            fund_advice = f"建议准备{funds_needed:.2f}资金完成目标建仓"
            fund_strategy = "分批买入，每次使用20%可用资金"
        else:
            funds_needed = 0
            fund_advice = "已完成目标建仓，无需额外资金"
            fund_strategy = "可将获利部分用于其他标的"
        
        # 负成本进度
        if negative_cost_possible:
            negative_cost_progress = 100
            negative_cost_color = "success"
            negative_cost_advice = f"已可实现负成本持仓，卖出{negative_cost_shares}股后剩余股票成本为0"
            negative_cost_detail = f"卖出{negative_cost_shares}股获得{negative_cost_shares * current_price:.2f}，覆盖剩余{remaining_shares}股成本"
        elif unrealized_profit > 0:
            progress_percent = (unrealized_profit / total_cost) * 100
            negative_cost_progress = min(progress_percent, 99)
            negative_cost_color = "primary"
            negative_cost_advice = f"距离负成本还差{(total_cost - unrealized_profit):.2f}"
            negative_cost_detail = f"当前盈利{unrealized_profit:.2f}，总成本{total_cost:.2f}，完成度{progress_percent:.1f}%"
        else:
            negative_cost_progress = 0
            negative_cost_color = "danger"
            negative_cost_advice = "当前为亏损状态，距离负成本较远"
            negative_cost_detail = f"需要股价上涨至少{(avg_cost * 2 - current_price):.2f}才可能实现负成本"
        
        # 时间预测
        if negative_cost_possible:
            time_prediction = "已可实现负成本"
        elif profit_rate > 0:
            months_needed = 12 * (1 - unrealized_profit / total_cost)
            time_prediction = f"预计{max(1, int(months_needed))}个月后可实现负成本"
        else:
            time_prediction = "暂无法预测"
        
        # 具体行动步骤
        if negative_cost_possible:
            action_steps = [
                f"1. 卖出{negative_cost_shares}股，获利{negative_cost_shares * current_price:.2f}",
                f"2. 保留{remaining_shares}股，成本降为0",
                "3. 继续持有，享受剩余股票的全部上涨收益"
            ]
        elif profit_rate > 15:
            action_steps = [
                f"1. 卖出{max(int(current_shares * 0.2), 1)}股，锁定部分利润",
                "2. 设置止盈位，保护剩余利润",
                "3. 等待回调后考虑再次买入"
            ]
        elif profit_rate < -10:
            action_steps = [
                f"1. 分批加仓，每次{max(int(target_shares * 0.1), 1)}股",
                "2. 设置-15%止损位，控制风险",
                "3. 耐心等待市场回暖"
            ]
        else:
            action_steps = [
                "1. 持有现有仓位，观察市场",
                f"2. 设置{(current_price * 1.1):.2f}卖出提醒",
                f"3. 设置{(current_price * 0.9):.2f}买入提醒"
            ]
        
        return {
            'negative_cost_possible': negative_cost_possible,
            'negative_cost_shares': negative_cost_shares,
            'negative_cost_proceeds': negative_cost_proceeds,
            'remaining_shares': remaining_shares,
            'remaining_cost': remaining_cost,
            'action': action,
            'suggestion': suggestion,
            'color': color,
            'volatility_risk': volatility_risk,
            'position_risk': position_risk,
            'band_advice': band_advice,
            'band_detail': band_detail,
            'band_profit_estimate': band_profit_estimate,
            'fund_advice': fund_advice,
            'fund_strategy': fund_strategy,
            'funds_needed': funds_needed,
            'negative_cost_advice': negative_cost_advice,
            'negative_cost_detail': negative_cost_detail,
            'negative_cost_color': negative_cost_color,
            'negative_cost_progress': negative_cost_progress,
            'time_prediction': time_prediction,
            'action_steps': action_steps
        }
    
    except Exception as e:
        return {
            'error': str(e),
            'negative_cost_possible': False,
            'action': "数据计算错误",
            'suggestion': f"错误: {str(e)}",
            'color': "danger"
        }

@app.route('/add_stock', methods=['GET', 'POST'])
def add_stock():
    """添加股票"""
    if request.method == 'POST':
        try:
            code = request.form['code'].upper()
            name = request.form['name']
            market = request.form['market']
            current_price = float(request.form['current_price'])
            target_shares = int(request.form['target_shares'])
            current_shares = int(request.form.get('current_shares', 0))
            avg_cost = float(request.form.get('avg_cost', current_price))
            initial_investment = float(request.form.get('initial_investment', current_shares * avg_cost))
            
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # 检查股票是否已存在
            cursor.execute("SELECT id FROM stocks WHERE code = ?", (code,))
            if cursor.fetchone():
                flash(f'股票 {code} 已存在！', 'warning')
                conn.close()
                return redirect(url_for('add_stock'))
            
            # 添加股票
            cursor.execute("""
                INSERT INTO stocks 
                (code, name, market, target_shares, current_shares, avg_cost, current_price, initial_investment)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (code, name, market, target_shares, current_shares, avg_cost, current_price, initial_investment))
            
            # 更新资金管理
            if current_shares > 0:
                stock_cost = current_shares * avg_cost
                cursor.execute("""
                    UPDATE fund_management 
                    SET invested_amount = invested_amount + ?,
                        available_funds = available_funds - ?
                    WHERE id = 1
                """, (stock_cost, stock_cost))
            
            conn.commit()
            conn.close()
            
            flash(f'股票 {code} 添加成功！', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            flash(f'添加失败: {str(e)}', 'error')
    
    return render_template('add_stock.html')

@app.route('/edit_stock/<int:stock_id>', methods=['GET', 'POST'])
def edit_stock(stock_id):
    """编辑股票"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        try:
            current_price = float(request.form['current_price'])
            target_shares = int(request.form['target_shares'])
            
            # 更新股票信息
            cursor.execute("""
                UPDATE stocks 
                SET current_price = ?, target_shares = ?
                WHERE id = ?
            """, (current_price, target_shares, stock_id))
            
            conn.commit()
            flash('股票信息更新成功！', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            flash(f'更新失败: {str(e)}', 'error')
    
    # 获取股票信息
    cursor.execute("""
        SELECT id, code, name, market, target_shares, current_shares, 
               avg_cost, current_price, initial_investment
        FROM stocks WHERE id = ?
    """, (stock_id,))
    
    stock = cursor.fetchone()
    if not stock:
        flash('股票不存在！', 'error')
        return redirect(url_for('index'))
    
    id, code, name, market, target_shares, current_shares, avg_cost, current_price, initial_investment = stock
    
    conn.close()
    
    return render_template('edit_stock.html', 
                         stock_id=id,
                         code=code,
                         name=name,
                         market=market,
                         target_shares=target_shares,
                         current_shares=current_shares,
                         avg_cost=avg_cost,
                         current_price=current_price,
                         initial_investment=initial_investment)

@app.route('/trades', methods=['GET', 'POST'])
def trades():
    """交易记录"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        try:
            stock_code = request.form['stock_code'].upper()
            trade_type = request.form['trade_type']
            shares = int(request.form['shares'])
            price = float(request.form['price'])
            fees = float(request.form.get('fees', 0))
            trade_date = request.form['trade_date']
            notes = request.form.get('notes', '')
            
            # 检查股票是否存在
            cursor.execute("SELECT id, current_shares, avg_cost FROM stocks WHERE code = ?", (stock_code,))
            stock = cursor.fetchone()
            if not stock:
                flash(f'股票 {stock_code} 不存在！', 'error')
                conn.close()
                return redirect(url_for('trades'))
            
            stock_id, current_shares, avg_cost = stock
            
            # 添加交易记录
            cursor.execute("""
                INSERT INTO trades 
                (stock_code, trade_type, shares, price, fees, trade_date, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (stock_code, trade_type, shares, price, fees, trade_date, notes))
            
            # 更新股票信息
            if trade_type == 'buy':
                # 买入：更新持仓数量和平均成本
                new_shares = current_shares + shares
                new_cost = (current_shares * avg_cost + shares * price + fees)
                new_avg_cost = new_cost / new_shares if new_shares > 0 else 0
                
                cursor.execute("""
                    UPDATE stocks 
                    SET current_shares = ?, avg_cost = ?, total_fees = total_fees + ?
                    WHERE code = ?
                """, (new_shares, new_avg_cost, fees, stock_code))
                
                # 更新资金管理
                trade_cost = shares * price + fees
                cursor.execute("""
                    UPDATE fund_management 
                    SET invested_amount = invested_amount + ?,
                        available_funds = available_funds - ?
                    WHERE id = 1
                """, (trade_cost, trade_cost))
                
            elif trade_type == 'sell':
                # 卖出：更新持仓数量
                if shares > current_shares:
                    flash(f'卖出股数不能大于当前持仓！', 'error')
                    conn.close()
                    return redirect(url_for('trades'))
                
                new_shares = current_shares - shares
                
                cursor.execute("""
                    UPDATE stocks 
                    SET current_shares = ?, total_fees = total_fees + ?
                    WHERE code = ?
                """, (new_shares, fees, stock_code))
                
                # 更新资金管理
                trade_proceeds = shares * price - fees
                cursor.execute("""
                    UPDATE fund_management 
                    SET invested_amount = invested_amount - ?,
                        available_funds = available_funds + ?
                    WHERE id = 1
                """, (shares * avg_cost, trade_proceeds))
            
            conn.commit()
            flash('交易记录添加成功！', 'success')
            return redirect(url_for('trades'))
            
        except Exception as e:
            flash(f'添加失败: {str(e)}', 'error')
    
    # 获取所有股票
    cursor.execute("SELECT code, name FROM stocks ORDER BY code")
    stocks = cursor.fetchall()
    
    # 获取交易记录
    cursor.execute("""
        SELECT t.id, t.stock_code, s.name, t.trade_type, t.shares, t.price, 
               t.fees, t.trade_date, t.notes, t.created_at
        FROM trades t
        JOIN stocks s ON t.stock_code = s.code
        ORDER BY t.trade_date DESC, t.created_at DESC
    """)
    trades_list = cursor.fetchall()
    
    conn.close()
    
    return render_template('trades.html', stocks=stocks, trades=trades_list)

@app.route('/strategy/<stock_code>')
def strategy(stock_code):
    """策略分析"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 获取股票信息
        cursor.execute("""
            SELECT id, code, name, market, target_shares, current_shares, 
                   avg_cost, current_price, initial_investment
            FROM stocks WHERE code = ?
        """, (stock_code,))
        
        stock = cursor.fetchone()
        if not stock:
            flash(f'股票 {stock_code} 不存在！', 'error')
            conn.close()
            return redirect(url_for('index'))
        
        id, code, name, market, target_shares, current_shares, avg_cost, current_price, initial_investment = stock
        
        # 计算策略
        strategy_data = calculate_negative_cost_strategy(
            code, current_price, current_shares, avg_cost, target_shares
        )
        
        # 获取交易历史
        cursor.execute("""
            SELECT trade_type, shares, price, trade_date
            FROM trades
            WHERE stock_code = ?
            ORDER BY trade_date DESC
        """)
        trades = cursor.fetchall()
        
        # 计算基本数据
        current_value = current_shares * current_price
        total_cost = current_shares * avg_cost
        unrealized_profit = current_value - total_cost
        profit_rate = (unrealized_profit / total_cost * 100) if total_cost > 0 else 0
        
        conn.close()
        
        return render_template('strategy.html',
                             stock_id=id,
                             code=code,
                             name=name,
                             market=market,
                             target_shares=target_shares,
                             current_shares=current_shares,
                             avg_cost=avg_cost,
                             current_price=current_price,
                             current_value=current_value,
                             total_cost=total_cost,
                             unrealized_profit=unrealized_profit,
                             profit_rate=profit_rate,
                             initial_investment=initial_investment,
                             strategy=strategy_data,
                             trades=trades)
        
    except Exception as e:
        flash(f'加载策略分析失败: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/fund_management', methods=['GET', 'POST'])
def fund_management():
    """资金管理"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        try:
            total_capital = float(request.form['total_capital'])
            available_funds = float(request.form['available_funds'])
            profit_reinvest_ratio = float(request.form['profit_reinvest_ratio'])
            
            # 更新资金管理
            cursor.execute("""
                UPDATE fund_management 
                SET total_capital = ?, available_funds = ?, profit_reinvest_ratio = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            """, (total_capital, available_funds, profit_reinvest_ratio))
            
            conn.commit()
            flash('资金管理信息更新成功！', 'success')
            return redirect(url_for('fund_management'))
            
        except Exception as e:
            flash(f'更新失败: {str(e)}', 'error')
    
    # 获取资金管理信息
    cursor.execute("""
        SELECT total_capital, available_funds, invested_amount, profit_reinvest_ratio, updated_at
        FROM fund_management
        WHERE id = 1
    """)
    
    fund_data = cursor.fetchone()
    if not fund_data:
        # 创建初始资金管理记录
        cursor.execute("""
            INSERT INTO fund_management (total_capital, available_funds, invested_amount, profit_reinvest_ratio)
            VALUES (10000, 10000, 0, 0.5)
        """)
        conn.commit()
        
        cursor.execute("""
            SELECT total_capital, available_funds, invested_amount, profit_reinvest_ratio, updated_at
            FROM fund_management
            WHERE id = 1
        """)
        fund_data = cursor.fetchone()
    
    total_capital, available_funds, invested_amount, profit_reinvest_ratio, updated_at = fund_data
    
    # 获取投资组合统计
    cursor.execute("""
        SELECT SUM(current_shares * current_price) as total_value,
               SUM(current_shares * avg_cost) as total_cost
        FROM stocks
    """)
    
    portfolio_data = cursor.fetchone()
    total_value = portfolio_data[0] or 0
    total_cost = portfolio_data[1] or 0
    
    # 计算总盈亏
    total_profit = total_value - total_cost
    total_profit_rate = (total_profit / total_cost * 100) if total_cost > 0 else 0
    
    # 计算资金分配建议
    if available_funds > 0:
        # 建议将可用资金分配到不同股票
        cursor.execute("""
            SELECT code, name, target_shares, current_shares, current_price
            FROM stocks
            WHERE current_shares < target_shares
            ORDER BY (target_shares - current_shares) * current_price DESC
        """)
        
        allocation_candidates = cursor.fetchall()
        
        allocation_suggestions = []
        remaining_funds = available_funds
        
        for code, name, target_shares, current_shares, current_price in allocation_candidates:
            if remaining_funds <= 0:
                break
                
            shares_gap = target_shares - current_shares
            if shares_gap <= 0:
                continue
                
            funds_needed = shares_gap * current_price
            allocation_amount = min(funds_needed, remaining_funds, available_funds * 0.3)
            shares_to_buy = int(allocation_amount / current_price)
            
            if shares_to_buy > 0:
                allocation_suggestions.append({
                    'code': code,
                    'name': name,
                    'shares': shares_to_buy,
                    'amount': shares_to_buy * current_price,
                    'percentage': (shares_to_buy * current_price / available_funds) * 100
                })
                
                remaining_funds -= shares_to_buy * current_price
    else:
        allocation_suggestions = []
    
    conn.close()
    
    return render_template('fund_management.html',
                         total_capital=total_capital,
                         available_funds=available_funds,
                         invested_amount=invested_amount,
                         profit_reinvest_ratio=profit_reinvest_ratio,
                         updated_at=updated_at,
                         total_value=total_value,
                         total_cost=total_cost,
                         total_profit=total_profit,
                         total_profit_rate=total_profit_rate,
                         allocation_suggestions=allocation_suggestions)

@app.route('/health')
def health_check():
    """健康检查"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 检查数据库表
        cursor.execute("SELECT COUNT(*) FROM stocks")
        stock_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM trades")
        trade_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM fund_management")
        fund_count = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected',
            'tables': {
                'stocks': stock_count,
                'trades': trade_count,
                'fund_management': fund_count
            },
            'features': {
                'negative_cost_strategy': True,
                'trade_tracking': True,
                'fund_management': True,
                'risk_assessment': True
            },
            'environment': {
                'db_path': DB_PATH,
                'render_volume': os.environ.get('RENDER_EXTERNAL_VOLUME', 'not_available'),
                'python_version': '.'.join(map(str, [sys.version_info.major, sys.version_info.minor, sys.version_info.micro]))
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/stocks')
def api_stocks():
    """API: 获取所有股票"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT code, name, market, target_shares, current_shares, 
                   avg_cost, current_price, initial_investment
            FROM stocks ORDER BY created_at DESC
        """)
        
        stocks = cursor.fetchall()
        conn.close()
        
        stock_list = []
        for stock in stocks:
            code, name, market, target_shares, current_shares, avg_cost, current_price, initial_investment = stock
            
            current_value = current_shares * current_price
            total_cost = current_shares * avg_cost
            profit = current_value - total_cost
            
            stock_list.append({
                'code': code,
                'name': name,
                'market': market,
                'target_shares': target_shares,
                'current_shares': current_shares,
                'avg_cost': avg_cost,
                'current_price': current_price,
                'current_value': current_value,
                'total_cost': total_cost,
                'profit': profit,
                'profit_rate': (profit / total_cost * 100) if total_cost > 0 else 0,
                'initial_investment': initial_investment
            })
        
        return jsonify({'stocks': stock_list})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/strategy/<stock_code>')
def api_strategy(stock_code):
    """API: 获取股票策略分析"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT code, name, market, target_shares, current_shares, 
                   avg_cost, current_price, initial_investment
            FROM stocks WHERE code = ?
        """, (stock_code,))
        
        stock = cursor.fetchone()
        if not stock:
            return jsonify({'error': f'股票 {stock_code} 不存在'}), 404
        
        code, name, market, target_shares, current_shares, avg_cost, current_price, initial_investment = stock
        
        # 计算策略
        strategy = calculate_negative_cost_strategy(
            code, current_price, current_shares, avg_cost, target_shares
        )
        
        # 基础数据
        current_value = current_shares * current_price
        total_cost = current_shares * avg_cost
        profit = current_value - total_cost
        
        result = {
            'code': code,
            'name': name,
            'market': market,
            'target_shares': target_shares,
            'current_shares': current_shares,
            'avg_cost': avg_cost,
            'current_price': current_price,
            'current_value': current_value,
            'total_cost': total_cost,
            'profit': profit,
            'profit_rate': (profit / total_cost * 100) if total_cost > 0 else 0,
            'initial_investment': initial_investment,
            'strategy': strategy
        }
        
        conn.close()
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

