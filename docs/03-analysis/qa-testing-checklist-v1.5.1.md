# QA Testing Checklist - MAX Meeting v1.5.1

**Date:** 2026-01-30
**Status:** Ready for Manual Testing
**All Code Changes Verified:** 10/12 (83%)

---

## Pre-Testing Setup

### Browser and Environment
- [ ] Open browser (Chrome/Firefox/Safari)
- [ ] Navigate to http://localhost:3000
- [ ] Open developer console (F12)
- [ ] Check Network tab for Request IDs (X-Request-ID headers)

### Log Monitoring (Optional but Recommended)
```bash
# In separate terminal, monitor backend logs
cd /home/et/max-ops/max-meeting
tail -f backend/app.log 2>/dev/null || ps aux | grep uvicorn
```

---

## Test 1: 3-Level Agenda Creation & Display

### Test 1.1: Create 3-Level Agenda
- [ ] Click "New Meeting"
- [ ] Enter meeting title
- [ ] Enter agenda text with 3 levels:
  ```
  1. 전략 수립 (Level 1)
     1.1. 시장 분석 (Level 2)
        1.1.1. 경쟁사 분석 (Level 3)
  ```
- [ ] Click "Parse Agenda" or "Create"
- [ ] Verify system accepts 3+ levels without error

### Test 1.2: Settings Page Display
- [ ] Open created meeting
- [ ] Navigate to Settings/Configuration
- [ ] Look for agenda section
- [ ] Verify all 3 levels visible:
  - [ ] Parent item ("전략 수립")
  - [ ] Child item ("시장 분석")
  - [ ] Grandchild item ("경쟁사 분석")
- [ ] Verify proper indentation hierarchy
- [ ] **Issue #2 Verified:** If all 3 levels visible with correct hierarchy

### Test 1.3: Hierarchical Numbering
- [ ] In settings/results page, check agenda numbering
- [ ] Verify format is hierarchical:
  - [ ] "1" for parent
  - [ ] "1.1" for child
  - [ ] "1.1.1" for grandchild
- [ ] **Issue #6 Verified:** If numbering matches 1.2.1 format

**Test Results:**
- Issue #1 (3-level save): [ ] PASS / [ ] FAIL
- Issue #2 (3-level display): [ ] PASS / [ ] FAIL
- Issue #6 (hierarchical numbering): [ ] PASS / [ ] FAIL

---

## Test 2: Recording and STT Progress

### Test 2.1: Recording Interface
- [ ] Open the meeting for recording
- [ ] Look for restart button
- [ ] Verify button text says "회의 재시작" (NOT "다시 녹음")
- [ ] **Issue #3 Verified:** If button says "회의 재시작"

### Test 2.2: STT Progress Bar
- [ ] Click "Start Recording"
- [ ] Speak some test phrases (10-15 seconds)
- [ ] Watch progress bar:
  - [ ] Should show values between 1% and 99% during recording
  - [ ] Should NOT show 0%
  - [ ] Should NOT jump to 100% while still recording
- [ ] Stop recording
- [ ] Watch progress bar reach 100%
- [ ] Wait for STT to complete

### Test 2.3: Restart Functionality
- [ ] While recording, click "회의 재시작" button
- [ ] Verify dialog/confirmation appears
- [ ] Confirm restart
- [ ] Verify recording resets to beginning
- [ ] Check timestamp is reset (0:00)
- [ ] **Issue #8 Verified:** If timestamp shows 0:00 after restart
- [ ] Start new recording and verify progress tracking works

**Test Results:**
- Issue #3 (terminology): [ ] PASS / [ ] FAIL
- Issue #4 (progress 1%-99%): [ ] PASS / [ ] FAIL
- Issue #8 (timestamp reset): [ ] PASS / [ ] FAIL

---

## Test 3: Summary Generation

### Test 3.1: Generate Summary
- [ ] Record a short audio clip (or use existing)
- [ ] Navigate to Summary/Results tab
- [ ] Click "Generate Summary" or "Create from Recording"
- [ ] Watch progress bar:
  - [ ] Should show 1-99% during generation
  - [ ] Should NOT get stuck at 95%
  - [ ] Should reach 100% when complete
- [ ] **Issue #5 Verified:** If progress reaches 100% (not stuck at 95%)

### Test 3.2: Summary Content
- [ ] Once generation completes, review summary:
  - [ ] Verify summary text appears
  - [ ] Check that 3-level agendas are included
  - [ ] Verify agenda hierarchy is shown (e.g., "1.1.1 경쟁사 분석")
- [ ] **Issue #9 Verified:** If 3-level agendas appear in summary
- [ ] **Issue #11 Verified:** If agenda hierarchy preserved in summary

### Test 3.3: Summary Editor
- [ ] Click "Edit Summary" or similar
- [ ] Verify summary editor opens
- [ ] Check all UI text is in Korean:
  - [ ] "요약" (Summary)
  - [ ] "편집" (Edit)
  - [ ] "저장" (Save)
  - [ ] "취소" (Cancel)
  - [ ] Other buttons/labels
- [ ] Edit some text
- [ ] Save changes
- [ ] Verify changes persist
- [ ] **Issue #10 Verified:** If UI text is in Korean

**Test Results:**
- Issue #5 (AI completion): [ ] PASS / [ ] FAIL
- Issue #9 (3-level in summary): [ ] PASS / [ ] FAIL
- Issue #10 (Korean UI): [ ] PASS / [ ] FAIL
- Issue #11 (hierarchy in summary): [ ] PASS / [ ] FAIL

---

## Test 4: UI Improvements

### Test 4.1: Dropdown Display
- [ ] Navigate to "Dialogue Content" or "대화 내용" tab
- [ ] Click dropdown/expand if needed
- [ ] Verify content displays correctly:
  - [ ] Text is NOT truncated
  - [ ] No horizontal scroll needed
  - [ ] Dropdown doesn't overlap other elements
  - [ ] Z-index/layering is correct
- [ ] Close dropdown
- [ ] **Issue #7 Verified:** If dropdown displays fully without truncation

### Test 4.2: Responsive Display
- [ ] Resize browser window
- [ ] Test on different screen sizes (desktop, tablet, mobile view)
- [ ] Verify all dropdowns/content adapts properly
- [ ] No text overlap or cutoff

**Test Results:**
- Issue #7 (dropdown truncation): [ ] PASS / [ ] FAIL

---

## Test 5: Action Items

### Test 5.1: Add Action Items
- [ ] On the meeting page, find "Action Items" or "실행항목" section
- [ ] Click "Add Item" or "+"
- [ ] Enter action item details:
  - [ ] Title (e.g., "자료 준비")
  - [ ] Assignee (if applicable)
  - [ ] Due date (if applicable)
- [ ] Save
- [ ] Verify item appears in list

### Test 5.2: Action Item Persistence
- [ ] Close the meeting page
- [ ] Navigate back to the same meeting
- [ ] Open Action Items section
- [ ] Verify previously added items are still there
- [ ] **Issue #12 Verified:** If action items persist after page refresh

### Test 5.3: Manage Action Items
- [ ] Mark item as complete (if checkbox available)
- [ ] Edit an item
- [ ] Delete an item
- [ ] Verify all operations work

**Test Results:**
- Issue #12 (action items): [ ] PASS / [ ] FAIL

---

## Test 6: Data Persistence

### Test 6.1: Session Persistence
- [ ] Create a meeting with:
  - [ ] 3-level agenda
  - [ ] Recording
  - [ ] Generated summary
  - [ ] Action items
- [ ] Close browser completely
- [ ] Reopen http://localhost:3000
- [ ] Navigate back to the meeting
- [ ] Verify all data is intact:
  - [ ] 3-level agenda present
  - [ ] Recording time preserved
  - [ ] Summary text present
  - [ ] Action items present

### Test 6.2: Settings Persistence
- [ ] Make changes to meeting settings
- [ ] Close page
- [ ] Reopen meeting
- [ ] Verify settings saved

**Test Results:**
- All data persistence: [ ] PASS / [ ] FAIL

---

## Test 7: Error Handling

### Test 7.1: Monitor for Errors
- [ ] During all above tests, check:
  - [ ] Browser console for JavaScript errors (red text)
  - [ ] Network tab for failed requests (red entries)
  - [ ] Backend logs for ERROR level messages (if monitoring)
- [ ] **Expected:** No ERROR level logs
- [ ] **Expected:** All network requests succeed (200-299 status codes)

### Test 7.2: Request ID Tracking
- [ ] Open Network tab
- [ ] Perform an action (e.g., save meeting)
- [ ] Click on any network request
- [ ] Go to "Headers" tab
- [ ] Verify "X-Request-ID" header present
- [ ] All related requests should have same Request ID

**Test Results:**
- No errors found: [ ] PASS / [ ] FAIL
- Request ID tracking: [ ] PASS / [ ] FAIL

---

## Summary of Results

### Pass/Fail by Issue

| Issue | Description | Status |
|-------|-------------|--------|
| #1 | 3-level agenda save | [ ] PASS / [ ] FAIL |
| #2 | 3-level display | [ ] PASS / [ ] FAIL |
| #3 | Terminology fix | [ ] PASS / [ ] FAIL |
| #4 | STT progress 1%-99% | [ ] PASS / [ ] FAIL |
| #5 | AI completion (not 95%) | [ ] PASS / [ ] FAIL |
| #6 | Hierarchical numbering | [ ] PASS / [ ] FAIL |
| #7 | Dropdown truncation | [ ] PASS / [ ] FAIL |
| #8 | Timestamp reset | [ ] PASS / [ ] FAIL |
| #9 | 3-level in summary | [ ] PASS / [ ] FAIL |
| #10 | Korean UI | [ ] PASS / [ ] FAIL |
| #11 | Hierarchy in summary | [ ] PASS / [ ] FAIL |
| #12 | Action items | [ ] PASS / [ ] FAIL |

### Overall Results
- **Total Tests:** 12
- **Passed:** [ ] / 12
- **Failed:** [ ] / 12
- **Pass Rate:** [ ] %

### Issues Found During Testing

**Critical Issues:**
- [ ] None
- [ ] (list any)

**Medium Issues:**
- [ ] None
- [ ] (list any)

**Minor Issues/Suggestions:**
- [ ] None
- [ ] (list any)

---

## Sign-Off

**Tested By:** ___________________
**Date:** ___________________
**Time Spent:** _____ minutes

**Overall Status:**
- [ ] ALL TESTS PASSED - Ready for Production
- [ ] MINOR ISSUES - Ready with notes
- [ ] CRITICAL ISSUES - Needs more work

**Notes/Comments:**
```
(Add any observations or issues found)




```

---

## If Issues Found

If you find any failures or errors:

1. **Document Exact Steps to Reproduce**
2. **Note Error Messages** (from console or logs)
3. **Screenshot** (if visual issue)
4. **Request ID** (from Network tab) for server-side issues
5. **Create Issue** with above information

**QA Report Location:**
`/home/et/max-ops/max-meeting/docs/03-analysis/zero-script-qa-20260130.md`

