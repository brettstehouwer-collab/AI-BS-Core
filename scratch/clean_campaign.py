import sqlite3

conn = sqlite3.connect(r'C:\AI-BS\saved_data\rec_debut.db')
c = conn.cursor()
clean_text = """CONGRATULATIONS! YOU'VE BEEN SELECTED TO GET YOUR ATHLETIC PORTFOLIO IN FRONT OF 850 COLLEGE COACHES NATIONWIDE!

I'm Dennis Bell, former New York Knick and President of Recreational Debut. We've helped more than 100 student-athletes get recruited, and now we want to help you get noticed.

If you're serious about playing college sports, don't wait for coaches to find you.
📱 Call or text: 616-291-5227
📧 Email: dbell002@sbcglobal.net
✅ Register FREE: RecDebut.com

College programs across the country are looking for talented student-athletes. That opportunity could include YOU.

Dennis Bell
Former New York Knicks
President, Recreational Debut
616-291-5227 • RecDebut.com • dbell002@sbcglobal.net"""

c.execute('UPDATE rec_debut_campaigns SET message_body = ? WHERE id = 1', (clean_text,))
conn.commit()
conn.close()
print('Cleaned message text in campaign.')
