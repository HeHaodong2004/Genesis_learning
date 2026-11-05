// Dependency-free course contract checks. Browser interactions are checked separately.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const root = __dirname;
const sandbox = {window:{}};
vm.runInNewContext(fs.readFileSync(path.join(root,'dist/course-data.js'),'utf8'),sandbox);
const course=sandbox.window.COURSE_DATA;
const lessons=new Set(), steps=new Set();
assert.equal(course.lessons.length,7);
for(const lesson of course.lessons){
  assert(!lessons.has(lesson.id)); lessons.add(lesson.id);
  assert(lesson.title && lesson.docPath && lesson.gates.length && lesson.steps.length);
  for(const step of lesson.steps){
    const key=lesson.id+':'+step.id;
    assert(!steps.has(key)); steps.add(key);
    for(const field of ['title','body','expected','prompt']) assert.equal(typeof step[field],'string');
    assert(['read','predict','run','implement','verify','reflect'].includes(step.kind));
    if(step.file) assert(Object.hasOwn(course.files,step.file),'missing source '+step.file);
  }
}
assert.equal(steps.size,46);
assert.equal(course.roadmap.length,4);
for(const name of ['index.html','styles.css','app.js']) assert(fs.statSync(path.join(root,'dist',name)).size>0);
console.log(`PASS: ${lessons.size} chapters, ${steps.size} steps, ${Object.keys(course.files).length} source files`);
