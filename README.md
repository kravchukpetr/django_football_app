# ⚽ Football Stats - Django Prediction Application

A comprehensive Django web application for football match predictions, group competitions, and statistical tracking.

## 🌟 Features

### 🏆 **Core Functionality**
- **Match Predictions**: Individual and bulk prediction capabilities
- **User Groups**: Create prediction groups and compete with friends
- **League Management**: Comprehensive league, team, and match organization
- **Scoring System**: Points-based prediction scoring (5 points for exact score, 2 for correct result)
- **Real-time Statistics**: Automatic accuracy and performance tracking

### 📊 **User Features**
- **Prediction Center**: Easy-to-use interface for making predictions
- **Personal Dashboard**: Track your prediction history and statistics
- **Group Leaderboards**: Compete with friends in prediction groups
- **Performance Analytics**: Detailed statistics by league and overall

### 🎯 **Group System**
- **Public/Private Groups**: Create open groups or invite-only competitions
- **League Selection**: Groups choose which leagues to predict
- **Role Management**: Admin, moderator, and member roles
- **Join Codes**: Easy group joining with unique codes

### 🔧 **Admin Features**
- **Comprehensive Admin Panel**: Full CRUD operations for all models
- **Bulk Operations**: Mass updates and statistics calculations
- **User Management**: Extended user profiles with prediction stats
- **Match Management**: Schedule matches and update results

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- pip (Python package manager)
- Virtual environment (recommended)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd django_app
   ```

2. **Create and activate virtual environment**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run database migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create superuser account**
   ```bash
   python manage.py createsuperuser
   ```

6. **Start development server**
   ```bash
   python manage.py runserver
   ```

7. **Access the application**
   - Main site: http://127.0.0.1:8000/
   - Admin panel: http://127.0.0.1:8000/admin/

## 📋 Usage Guide

### 🔧 **Initial Setup (Admin)**

1. **Access Admin Panel**
   - Go to http://127.0.0.1:8000/admin/
   - Login with superuser credentials

2. **Add Basic Data**
   ```
   Countries → Add countries (e.g., England, Spain, Germany)
   Leagues → Create leagues (Premier League, La Liga, etc.)
   Teams → Add teams and assign to leagues
   Matches → Schedule upcoming matches
   ```

3. **Create User Groups**
   ```
   User groups → Create prediction groups
   Group memberships → Add users to groups
   ```

### 👤 **User Workflow**

1. **Join Groups**
   - Browse public groups or use join codes
   - Get invited to private groups

2. **Make Predictions**
   - Visit Prediction Center
   - Select matches to predict
   - Choose result and optionally exact scores
   - Set confidence level

3. **Track Performance**
   - View prediction history
   - Check group leaderboards
   - Monitor accuracy statistics

## 🏗️ **Application Structure**

```
football_stats/
├── football_app/           # Main Django app
│   ├── models.py           # Database models
│   ├── views.py            # View controllers
│   ├── forms.py            # Django forms
│   ├── admin.py            # Admin configuration
│   ├── urls.py             # URL routing
│   └── templates/          # HTML templates
│       └── football_app/
│           ├── base.html
│           ├── home.html
│           ├── league_*.html
│           ├── user_*.html
│           ├── group_*.html
│           └── prediction_*.html
├── football_stats/         # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── manage.py               # Django management script
```

## 📊 **Database Models**

### Core Models
- **Country**: Football countries with leagues
- **League**: Football leagues within countries
- **Team**: Football teams assigned to leagues
- **MatchResult**: Individual match data and results

### Prediction Models
- **MatchPredict**: User predictions for matches
- **UserGroup**: Prediction groups for competition
- **GroupMembership**: User membership in groups
- **GroupInvitation**: Group invitation system

### User Models
- **UserProfile**: Extended user information and statistics

## 🎯 **Scoring System**

| Prediction Type | Points Awarded |
|-----------------|----------------|
| Exact Score Match | 5 points |
| Correct Result (W/L/D) | 2 points |
| Incorrect Prediction | 0 points |

## 🔗 **URL Structure**

```
/                           # Home dashboard
/leagues/                   # League list
/leagues/<id>/              # League detail with standings
/users/                     # User leaderboard
/users/<id>/                # User profile
/groups/                    # Public groups
/groups/<id>/               # Group detail with leaderboard
/predictions/               # Prediction center
/predictions/make/<id>/     # Individual prediction form
/predictions/bulk/          # Bulk prediction form
/predictions/my/            # Personal prediction history
/admin/                     # Django admin panel
```

## 🛠️ **Technologies Used**

- **Backend**: Django 4.2.24, Python 3.9+
- **Database**: SQLite (development), PostgreSQL ready
- **Frontend**: Bootstrap 5, HTML5, CSS3, JavaScript
- **Icons**: Font Awesome 6
- **Admin**: Django Admin with custom configurations

## 📈 **Features in Detail**

### 🎯 **Prediction System**
- **Smart Validation**: Prevents predictions on finished/live matches
- **Deadline Enforcement**: Automatic prediction cutoff
- **Bulk Operations**: Predict multiple matches simultaneously
- **Confidence Tracking**: Rate prediction confidence (1-100%)

### 👥 **Group Management**
- **Flexible Membership**: Public groups with join codes
- **Private Invitations**: Invite-only groups
- **Role-Based Access**: Admin, moderator, member roles
- **League Selection**: Groups choose specific leagues to predict

### 📊 **Statistics & Analytics**
- **Real-time Updates**: Automatic statistics calculation
- **Performance Metrics**: Accuracy, total points, predictions made
- **League Breakdown**: Performance by individual leagues
- **Group Rankings**: Leaderboards within prediction groups

### 🔧 **Admin Features**
- **Comprehensive Management**: Full CRUD for all models
- **Batch Operations**: Update multiple records simultaneously
- **Statistics Calculation**: Recalculate user/group statistics
- **Match Management**: Schedule matches and update results

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🐛 **Troubleshooting**

### Common Issues

1. **Migration Errors**
   ```bash
   python manage.py makemigrations football_app
   python manage.py migrate
   ```

2. **Static Files Issues**
   ```bash
   python manage.py collectstatic
   ```

3. **Admin Access Issues**
   ```bash
   python manage.py createsuperuser
   ```

### Database Reset (Development)
```bash
# Delete database file
rm db.sqlite3

# Remove migration files
rm football_app/migrations/0*.py

# Recreate migrations and database
python manage.py makemigrations football_app
python manage.py migrate
python manage.py createsuperuser
```

## 📞 **Support**

For support, please create an issue in the repository or contact the development team.

---

⚽ **Happy Predicting!** 🏆
