from django.urls import path 
from . import views
from .views import *

urlpatterns = [
    path('', views.landing, name = 'landing'),

    path("accounts/api-register/", register_user, name="api-register"),
    path("accounts/api-login/", login_user, name="api-login"),
    path("accounts/api-create-test/", views.create_test, name="api-create-test"),

    path("register/", register_page, name="register"),
    path("login/", login_page, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("test-generator/", views.test_generator_page, name="test-generator"),
    path("tests/", views.test_list_page, name="test-list"),
    path("tests/<int:test_id>/", views.test_detail_page, name="test-detail"),
    path("tests/<int:test_id>/update-name/", views.update_test_name, name="update-test-name"),
    path("tests/<int:test_id>/generate-pdf/", views.generate_pdf_api, name="generate-pdf"),
    path("tests/<int:test_id>/duplicate/", views.duplicate_test_api, name="duplicate-test"),
    path("tests/<int:test_id>/delete/", views.delete_test_api, name="delete-test"),
    path("tests/<int:test_id>/upload-submissions/", views.upload_submissions, name="upload-submissions"),
    path("tests/<int:test_id>/submissions/", views.get_test_submissions, name="get-submissions"),
    path("tests/<int:test_id>/submissions/<int:submission_id>/", views.submission_detail_page, name="submission-detail"),
    path("tests/<int:test_id>/submissions/<int:submission_id>/update-name/", views.update_submission_name, name="update-submission-name"),
    path("tests/<int:test_id>/analytics/", views.test_analytics_api, name="test-analytics"),
    path("tests/<int:test_id>/export/", views.export_results_csv, name="export-results"),

    # Student Portal
    path("student/", views.student_dashboard, name="student-dashboard"),
    path("student/enroll/", views.enroll_in_test, name="enroll-in-test"),
    path("student/test/<int:test_id>/result/", views.student_test_result, name="student-test-result"),
]
