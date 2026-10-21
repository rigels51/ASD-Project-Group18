
# Student 4 – Yi Zhang - Post-Commit CI/CD Testing Report

## Student Information
- Student: Student 4 – Yi Zhang
- Feature: Course & Enrolment Management
- Branch: Student-4-release2

## GitHub Actions
- Workflow: Yi Zhang - Course and Enrollment
- Workflow Run: #39
- Commit: 2a17253
- Status: Success

## Tested API Endpoints

### Test 1: GET /courses
- Purpose: Retrieve the course list.
- Test: test_get_courses_returns_course_table
- Expected: HTTP 200 and HTML containing course data.
- Result: Passed

### Test 2: POST /courses
- Purpose: Create a new course.
- Test: test_post_courses_creates_course
- Expected: HTTP 201 for valid form data.
- Result: Passed

## Test Results
- Total Tests: 2
- Passed: 2
- Failed: 0
- CI Execution Time: 0.113 seconds
- Overall Status: PASS

## Conclusion
Both Course Management API endpoint tests passed
successfully through GitHub Actions. The workflow also
completed the required build and validation steps.
