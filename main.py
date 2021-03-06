import webapp2
import jinja2
import os
import re
import random
import hashlib
import hmac
import sqlite3
import urllib2
import time 
import datetime

from google.appengine.ext import db

#base template start

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
							   autoescape = True)

def render_str(template, **params):
	t = jinja_env.get_template(template)
	return t.render(params)

cook=''

class BaseHandler(webapp2.RequestHandler):
	def write(self, *a, **kw):
		self.response.out.write(*a, **kw)

	def render_str(self, template, **params):
		# params['user'] = self.user
		return render_str(template, **params)

	def render(self, template, **kw):
		self.write(self.render_str(template, **kw))

	def set_cookie(self, name, val):
		hashed = make_secure_val(val)
		cooked = name +'=' + hashed + ';Path=/'
		self.response.headers.add_header('Set-Cookie',str(cooked))

	def read_secure_cookie(self, name):
		cookie_val = self.request.cookies.get(name)
		if cookie_val and check_secure_val(cookie_val):
			return cookie_val

	def login(self, user):
		self.set_cookie('user_id', str(user.key().id()))

	def logout(self):
		self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')

	def initialize(self, *a, **kw):
		webapp2.RequestHandler.initialize(self, *a, **kw)
		uid = self.read_secure_cookie('user_id')

		if uid != None:
			uid = check_secure_val(uid)
			if uid != None:
				self.username = User.by_id(int(uid)).name
			else:
				self.username = None
		else:
			self.username = None


#base template end

secret='hiiis'
letters='abcdefghijklmnopqrstuvwxyz'

#hashing and salt stuff
def make_salt(length = 5):
	return ''.join(random.choice(letters) for x in xrange(length))

def make_pw_hash(name, pw, salt = None):
	if not salt:
		salt = make_salt()
	h = hashlib.sha256(name + pw + salt).hexdigest()
	return '%s,%s' % (salt, h)

def valid_pw(name, password, h):
	salt = h.split(',')[0]
	return h == make_pw_hash(name, password, salt)

def make_secure_val(val):
	return '%s|%s' % (val, hmac.new(secret, val).hexdigest())

def check_secure_val(secure_val):
	val = secure_val.split('|')[0]
	if secure_val == make_secure_val(val):
		return val

#hashing stuff ends

class User(db.Model):
	name = db.StringProperty(required=True)
	pw_hash = db.StringProperty(required=True)
	email = db.StringProperty()
	curr_balance = db.IntegerProperty(required=True)
	

	@classmethod
	def by_id(cls, uid):
		return User.get_by_id(uid)
	@classmethod
	def by_name(cls, name):
		u = User.all().filter('name =', name).get()
		return u


	@classmethod
	def register(cls, name, pw, email = None):
		pw_hash = make_pw_hash(name, pw)
		return User(name = name,
					pw_hash = pw_hash,
					email = email,
					curr_balance = 0)
	@classmethod
	def login(cls, name, pw):
		u = cls.by_name(name)
		# print(u)
		if u and valid_pw(name, pw, u.pw_hash):
			return u

# account details and related stuff
# 
conn = sqlite3.connect('account.db')
# conn.execute('''CREATE TABLE stocks
#                 (
#                  uname TEXT NOT NULL,
#                  stk_symbl TEXT NOT NULL,
#                  stk_qty INT NOT NULL,
#                  stk_price INT NOT NULL,
#                  time_stamp TIMESTAMP NOT NULL ) 
#                 ''')
# conn.execute('''
# 	CREATE TABLE transactionRequests
# 	(
# 		uname TEXT NOT NULL,
# 		stk_qty INT NOT NULL,
# 		stk_symbl TEXT NOT NULL,
# 		stk_price INT NOT NULL,
# 		time_stamp TIMESTAMP NOT NULL,
# 		status TEXT,
# 		PRIMARY KEY(uname, time_stamp))
# 	''')
t_now = datetime.datetime.now()
c = conn.cursor()
# inst = "INSERT INTO stocks VALUES ('test','TEST',10,100,?)"
# conn.execute("INSERT INTO stocks VALUES ('test','TEST',10,100,?)", (t_now,))
conn.commit()
c.execute('SELECT * FROM stocks')
print c.fetchall()
#conn.commit()
#functions for basic sign-up

USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(username):
	return username and USER_RE.match(username)

PASS_RE = re.compile(r"^.{3,20}$")
def valid_password(password):
	return password and PASS_RE.match(password)

EMAIL_RE  = re.compile(r'^[\S]+@[\S]+\.[\S]+$')
def valid_email(email):
	return not email or EMAIL_RE.match(email)

class SignUp(BaseHandler):
	def get(self):
		if self.username != None:
			self.redirect('/welcome')
			# if valid_username(self.username):
			# self.render('welcome.html', username = self.username)
		else:
			self.render('signup-form.html')

	def post(self):
		uname = self.request.get('username')
		password = self.request.get('password')
		verify = self.request.get('verify')
		email = self.request.get('email')

		# self.username = uname
		# self.password = password
		# self.email = email
		
		have_error = False
		
		params = dict(username = uname,
					  email = email)
		if not valid_username(uname):
			params['error_username'] = "That's not a valid username."
			have_error = True

		if not valid_password(password):
			params['error_password'] = "That wasn't a valid password."
			have_error = True
		elif password != verify:
			params['error_verify'] = "Your passwords didn't match."
			have_error = True

		if not valid_email(email):
			params['error_email'] = "That's not a valid email."
			have_error = True

		if have_error:
			self.render('signup-form.html', **params)
		else:
			# cooked = 'name=' + uname + ';Path=/'
			# self.response.headers.add_header('Set-Cookie',str(cooked))
			# self.set_cook('name', uname)
			u = User.by_name(uname)
			if u:
				msg = 'That user already exists.'
				self.render('signup-form.html', error_username = msg)
			else:
				# cooked = 'name=' + uname + ';Path=/'
				# self.response.headers.add_header('Set-Cookie',str(cooked))
				# self.set_cookie('name',uname)
				u = User.register(uname, password, email)
				u.put()
				self.login(u)
				self.redirect('/welcome')
				# self.login(u)
				# self.redirect('/blog')

class History(BaseHandler):
	def get(self):
		if self.username != None:
			params = {}
			sname = self.request.get('sname')
			c.execute("SELECT * from transactionRequests where uname=? and stk_symbl=?",(self.username, sname))
			params['stk_arr'] = c.fetchall()
			params['sname'] = sname
			params['username'] = self.username
			u = User.by_name(self.username)
			print(u.curr_balance)
			params['current_balance'] = u.curr_balance
			print(params) 
			self.render('history.html', **params)
		else:
			self.redirect('/login')

class Welcome(BaseHandler):
	def get(self):
		if self.username != None:
			params = {}
			params['username'] = self.username;
			c.execute("SELECT * FROM stocks where uname=?",(self.username,))
			dat = c.fetchall()
			params['stk_arr'] = dat
			u = User.by_name(self.username)
			print(u.curr_balance)
			params['current_balance'] = u.curr_balance 
			self.render('welcome.html', **params)
		else:
			self.redirect('/login')

class Login(BaseHandler):
	def get(self):
		if self.username != None:
			self.redirect('/welcome')
		self.render('login-form.html')
	
	def post(self):
		uname=self.request.get('username')
		passwd=self.request.get('password')
		u=User.login(uname, passwd)
		if u:
			self.login(u)
			self.redirect('/welcome')
		else:
			msg = 'Invalid login'
			self.render('login-form.html', error = msg)

class LogOut(BaseHandler):
	def get(self):
		self.logout()
		self.redirect('/login')

class SStock(BaseHandler):
	def get(self):
		sname = self.request.get('sname')
		params ={}
		params['stock_name']=sname
		u = User.by_name(self.username)
		params['current_balance'] = u.curr_balance
		params['username'] = self.username
		# c.execute("SELECT * FROM stocks where uname=?",(self.username,))
		# dat = c.fetchall()
		# self.render('stock_buy.html',stk_arr=dat)
		c.execute("SELECT * FROM stocks where uname=? and stk_symbl=?",(self.username,sname))
		global dat
		dat = c.fetchone()
		params['stk_arr']=dat
		print(dat)
		if dat:
			params['sell_opt'] = True
		self.render('stock_page.html',**params)
	
	def post(self):
		global dat
		req = self.request.get('req')
		sname = self.request.get('sname')
		stk_qty = self.request.get('qty')
		stk_price = self.request.get('stk_valu')
		u = User.by_name(self.username)
		print(req)
		if(req == 'buy'):
			print(req)
			t_now = datetime.datetime.now()
			tot_cost = int(stk_qty) * float(stk_price)
			if(u.curr_balance > tot_cost):
				u.curr_balance = int(u.curr_balance - tot_cost)
				u.put()
				c.execute("SELECT * FROM stocks where uname=? and stk_symbl=?",(self.username,sname))
				tmp = c.fetchone()
				conn.execute("INSERT INTO transactionRequests VALUES (?,?,?,?,?,?)", (self.username,stk_qty,sname,stk_price,t_now,"BUY--SUCCESS"))
				if tmp:
					print('in if')
					tmp2 = int(tmp[2])
					tmp3 = float(tmp[3])
					avg = ((tmp2 * tmp3) + int(stk_qty) * float(stk_price)) / (tmp2 + int(stk_qty))
					print(tmp2 + int(stk_qty))
					print("UPDATE stocks SET stk_qty=? and stk_price=? where stk_symbl=? and uname=?", ((tmp2 + int(stk_qty)), avg, sname, self.username, ))
					conn.execute("UPDATE stocks SET stk_qty=?, stk_price=? where uname=? and stk_symbl=?", ((tmp2 + int(stk_qty)), avg, self.username, sname))
					conn.commit()
				else:
					print('hello world')
					conn.execute("INSERT INTO stocks VALUES (?,?,?,?,?)", (self.username,sname,stk_qty,stk_price,t_now))
					conn.commit()
				print('helo transaction done')
				# self.write('transaction complete')
				# self.render('success.html')
				# time.sleep(5)
				self.redirect('/welcome')
			else:
				# self.render('regret.html')
				# time.sleep(5)
				# self.redirect('/stock_info?sname='+ sname)
				conn.execute("INSERT INTO transactionRequests VALUES (?,?,?,?,?,?)", (self.username,stk_qty,sname,stk_price,t_now,"BUY--FAILED"))
				conn.commit()
				self.redirect('/regret')

			# else
		if (req == 'sell'):
			t_now = datetime.datetime.now()
			tot_cost = int(stk_qty) * float(stk_price)
			if(int(stk_qty) > dat[2]):
				conn.execute("INSERT INTO transactionRequests VALUES (?,?,?,?,?,?)", (self.username,stk_qty,sname,stk_price,t_now,"SELL--FAILED"))
				print('naaah boy')
			if(int(stk_qty) == int(dat[2])):
				print('equal')
				conn.execute("INSERT INTO transactionRequests VALUES (?,?,?,?,?,?)", (self.username,stk_qty,sname,stk_price,t_now,"SELL--FAILED"))
				conn.execute("DELETE FROM stocks WHERE stk_symbl=?",(sname,))
				u.curr_balance = int(u.curr_balance + tot_cost)
				u.put()
			else:
				print('not hi')
				conn.execute("INSERT INTO transactionRequests VALUES (?,?,?,?,?,?)", (self.username,stk_qty,sname,stk_price,t_now,"SELL--SUCCESS"))
				tmp = int(dat[2]) - int(stk_qty)
				u.curr_balance = int(u.curr_balance + tot_cost)
				conn.execute("UPDATE stocks SET stk_qty=? where stk_symbl=?",(tmp,sname))
				u.put()
			conn.commit()
			self.redirect('/welcome')


class BuyS(BaseHandler):
	def get(self):
		c.execute("SELECT * FROM stocks where uname=?",(self.username,))
		dat = c.fetchall()
		self.render('stock_buy.html',stk_arr=dat)
	def post(self):
		sname = self.request.get('sname')
		stk_qty = self.request.get('qty')
		stk_price = 100
		t_now = datetime.datetime.now()
		conn.execute("INSERT INTO stocks VALUES (?,?,?,?,?)", (self.username,sname,stk_qty,stk_price,t_now))
		conn.commit()
		self.write('success')



class Regret(BaseHandler):
	def get(self):
		self.render('regret.html');


app = webapp2.WSGIApplication([
	('/sign_up', SignUp),
	('/login', Login),	
	('/logout', LogOut),	
	('/welcome', Welcome),
	('/history', History),
	('/stock_info', SStock),
	('/buy_stk', BuyS),
	('/regret', Regret)
], debug=True)
