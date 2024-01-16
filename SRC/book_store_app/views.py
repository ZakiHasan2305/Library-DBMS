from django.shortcuts import render, redirect
from django.db import connection
from django.http import HttpResponse
from django import forms
from datetime import datetime


# def fetch_user_name_given_ID(user_ID):
#     with connection.cursor() as cursor:
#         cursor.execute(f"SELECT fName, lName FROM user WHERE UserId = {user_ID};")
#         row = cursor.fetchone()

#         name = row[0] + " " + row[1]

#         return name

# def say_hello_to_user(request):
#     user_name = fetch_user_name_given_ID(0)
#     params = {"names": [user_name]}

#     return render(request, "hello_with_names.html", context=params)

def search_book_catalog(request):
    if request.method == "POST":
        post = request.POST

        book_name = post.get('book_title', '')
        book_genre = post.get('book_genre', '')
        price_range = post.get('price_range', '')

        query = "SELECT * FROM book WHERE title LIKE %s AND genre LIKE %s"
        params = [f"{book_name}%", f"{book_genre}%"]

        if price_range:
            query += " AND price <= %s"
            params.append(price_range)

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            books = cursor.fetchall()

        params = {'books': books}
        return render(request, "catalog.html", context=params)

    return render(request, "catalog.html", context={'books': []})

def personal_rec(request):
    global user

    if user:
        with connection.cursor() as cursor:

            cursor.execute("SELECT userID FROM User WHERE username = %s", [(user)])
            user_row = cursor.fetchone()
            
            if user_row:
                userID = user_row[0]
                cursor.execute(
                    "SELECT B.genre "
                    "FROM Orders O "
                    "JOIN Book B ON FIND_IN_SET(B.bookID, REPLACE(REPLACE(O.bookList, '(', ''), ')', '')) "
                    "WHERE O.userID = %s", [userID]
                )
                user_genre = [row[0] for row in cursor.fetchall()]

                genre_distribution = {}
                for genre in user_genre:
                    genre_distribution[genre] = genre_distribution.get(genre, 0) + 1

                cursor.execute("SELECT * FROM Book WHERE genre = %s ORDER BY numOfPurchases DESC LIMIT 5",
                               [str(max(genre_distribution, key=genre_distribution.get))])    

                recommendations = cursor.fetchall()
                print(recommendations)
                params = {'recommendations': recommendations}

                return render(request, 'recommendations.html', context=params)

    return render(request, 'recommendations.html', context={})

def trending(request):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT B.*, COUNT(O.bookList) AS order_count "
            "FROM Orders O "
            "JOIN Book B ON FIND_IN_SET(B.bookID, REPLACE(REPLACE(O.bookList, '(', ''), ')', '')) "
            "WHERE YEAR(O.orderDate) = YEAR(CURDATE()) "
            "GROUP BY B.bookID "
            "ORDER BY order_count DESC "
            "LIMIT 10"
        )
        trending_books = cursor.fetchall()

    params = {'trending_books': trending_books}
    return render(request, 'trending.html', context=params)

def generate_coupons():
    with connection.cursor() as cursor:
        cursor.execute("SELECT IFNULL(MAX(couponID), 0) FROM Coupon")
        next_coupon_id = cursor.fetchone()[0]

        # Increment the coupon ID for each row in the subquery
        cursor.execute(
            f"SET @nextCouponID := {next_coupon_id}"
        )

        # Insert new coupons
        cursor.execute(
            "INSERT INTO Coupon (couponID, expDate, discPercent, couponType, title, genre) "
            "SELECT "
            "@nextCouponID := @nextCouponID + 1 AS couponID, "
            "CURDATE() + INTERVAL 30 DAY AS expDate, "
            "15 AS discPercent, "
            "'Genre' AS couponType, "
            "CONCAT('Discount on ', g.genre, ' books') AS title, "
            "g.genre "
            "FROM ("
            "    SELECT "
            "        b.genre, "
            "        COUNT(*) AS genreCount "
            "    FROM Orders o "
            "    JOIN Book b ON FIND_IN_SET(b.bookID, o.bookList) "
            "    GROUP BY b.genre "
            "    HAVING genreCount > 5 "
            "    ORDER BY genreCount DESC "
            "    LIMIT 3 "
            ") AS g;"
        )

def analytics_coupon_creation(request):
    generate_coupons()
    with connection.cursor() as cursor:
            cursor.execute("SELECT couponID, title, discPercent, genre FROM Coupon ORDER BY couponID DESC LIMIT 3")
            last_three = cursor.fetchall()

    params = {'last_three': last_three}
    return render(request, 'analytics_coupon_creation.html', context = params)

cart = []

def addToCart(request):
    global cart
    if request.method == "POST":
        post = request.POST

        book_id = post.get('bookid_field', '')

        if not book_id.isdigit() or int(book_id) <= 0:
            return render(request, "cart.html", context={'error_message': 'Invalid Book ID'})

        query = "SELECT * FROM book WHERE bookID = %s"
        params = [book_id]

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            book = cursor.fetchone()

        if book:
            cart.append({
                'book_id': book[0],
                'title': book[1],
                'price': book[5]
            })
        else:
            return render(request, "cart.html", context={'error_message': 'Book not found'})

        params = {'carts': cart}
        return render(request, "cart.html", context=params)

    return render(request, "cart.html", context={'carts': cart})

def remFromCart(request):
    global cart

    if request.method == "POST":
        post = request.POST
        book_id = post.get('bookid_field', '')

        #use the WHERE clause to filter based on title, genre, and price range
        query = "SELECT * FROM book WHERE bookID = %s"
        params = [book_id]

        if book_id:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                book = cursor.fetchone()

            #check if the book exists in the cart before removing
            for item in cart:
                if item['book_id'] == book_id:
                    cart.remove(item)
                    break

            request.session['cart'] = cart

        #return the updated cart to the template
        params = {'carts': cart}
        return render(request, "cart.html", context=params)

    return render(request, "cart.html", context={'carts': cart})

def return_order_ids():
    with connection.cursor() as cursor:
        cursor.execute("SELECT orderID FROM orders")
            
        # Fetch all user IDs as a list
        order_ids = [row[0] for row in cursor.fetchall()]
            
        return order_ids
    
def return_user_id(username):
    with connection.cursor() as cursor:
        cursor.execute("SELECT userID FROM users WHERE username = %s", (username,))
        result = cursor.fetchone()

    # Check if a user with the given username exists
    if result:
        return result[0]  # Return the userID
    else:
        return None 
    

def create_order(username, bookList):
    userID = return_user_id(username)

    #Convert the bookList to a string of comma-separated IDs
    book_list_str = ",".join(map(str, bookList))

    #Get the current date in the format year-month-day
    order_date = datetime.now().strftime("%Y-%m-%d")

    #Fetch the prices of the books in the bookList from the book table
    with connection.cursor() as cursor:
        sql = "SELECT price FROM book WHERE bookID IN (%s)"
        cursor.execute(sql, (book_list_str,))
        
        # Fetch all prices as a list
        book_prices = [row[0] for row in cursor.fetchall()]

    cost = sum(book_prices)

    with connection.cursor() as cursor:
        existing_order_ids = return_order_ids()
        order_id = max(existing_order_ids, default=0) + 1

        sql = "INSERT INTO orders (orderID, userID, orderDate, cost, bookList) VALUES (%s, %s, %s, %s, %s)"

        cursor.execute(sql, (order_id, userID, order_date, cost, book_list_str))
        # Commit the changes to the database
        connection.commit()

    return order_id

# def create_order(request):
#     return 

user = ""

def login_form(request):
    global user
    if request.method == "POST":
        post = request.POST
        username = post.get("username_field", "")
        password = post.get("password_field", "")

        params = {"username": username, "password": password}

        if login_user(username, password):
            user = username
            #user is authenticated
            return redirect("/search-catalog")
        else:
            # User authentication failed, render the login form again with an error message
            params["error_message"] = "Invalid username or password."
            return render(request, "login.html", context=params)

    return render(request, "login.html")

def user_and_pass():
    with connection.cursor() as cursor:
        cursor.execute("SELECT username, pass FROM user")
        
        user_data = cursor.fetchall()
        
        user_dict = {username: password for username, password in user_data}
        
        return user_dict

def login_user(username, password):
    user_dict = user_and_pass()

    if username in user_dict:
        #username exists, check if the provided password matches
        if user_dict[username] == password:
            print("User logged in")
            return True  # Authentication successful
        else:
            return False  # Password doesn't match
    else:
        return False  # Username not found


def fetch_book_by_attribute(atr, input):
    books = []
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT * FROM Book WHERE {atr} = %s;", (input,))
        rows = cursor.fetchall()

        for row in rows:
            title = row[1]
            author_name = row[2] + " " + row[3]
            genre = row[4]
            price = row[5]

            # Create a dictionary for each book
            book_info = {
                'title': title,
                'author_name': author_name,
                'genre': genre,
                'price': price
            }

            books.append(book_info)
    return books

def return_user_ids():
    with connection.cursor() as cursor:
        cursor.execute("SELECT userID FROM user")
            
        # Fetch all user IDs as a list
        user_ids = [row[0] for row in cursor.fetchall()]
            
        return user_ids
   
def create_user(f_name, l_name, username, street, city, province, country, password):
    with connection.cursor() as cursor:
        # Generate a new user ID that doesn't already exist
        existing_user_ids = return_user_ids()
        user_id = max(existing_user_ids, default=0) + 1  # Generate a new ID one greater than the maximum existing ID

        # SQL query to insert a new user into the "user" table
        sql = "INSERT INTO user (userID, fName, lName, username, street, city, province, country, pass) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
            
        # Execute the query with the provided parameters
        cursor.execute(sql, (user_id, f_name, l_name, username, street, city, province, country, password))
            
        # Commit the changes to the database
        connection.commit()
        print("User added")
        # Optionally, you can return the newly created user's ID or any other information
        return user_id  # Returns the generated user ID
    
class CreateUserForm(forms.Form):
    f_name = forms.CharField(
        label='First Name',
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter First Name.."
            }
        )
    )
    l_name = forms.CharField(
        label='Last Name',
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter Last Name.."
            }
        )
    )
    username = forms.CharField(
        label='Username',
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter Username.."
            }
        )
    )
    street = forms.CharField(
        label='street',
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter street.."
            }
        )
    )
    city = forms.CharField(
        label='City',
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter City.."
            }
        )
    )
    province = forms.CharField(
        label='Province/State',
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter Province/State.."
            }
        )
    )
    country = forms.CharField(
        label='Country',
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter Country.."
            }
        )
    )
    password = forms.CharField(
        label='Password',
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter Password..",
                "type": "password"
            }
        )
    )
    
def create_user_form(request):
    if request.method == "POST":
        form = CreateUserForm(request.POST)
        if form.is_valid():
            f_name = form.cleaned_data["f_name"]
            l_name = form.cleaned_data["l_name"]
            username = form.cleaned_data["username"]
            street = form.cleaned_data["street"]
            city = form.cleaned_data["city"]
            province = form.cleaned_data["province"]
            country = form.cleaned_data["country"]
            password = form.cleaned_data["password"]

            create_user(f_name, l_name, username, street, city, province, country, password)
            params = {"f_name": [f_name], "l_name": [l_name], "username": [username], "street": [street], "city": [city], "province": [province], "country": [country], "pass": [password]}
            return render(request, "login.html", context=params)

    else:
        form = CreateUserForm()
        params = {"form": form}
        return render(request, "create_account.html", context=params)