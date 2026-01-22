import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EditItem } from './edit-item';

describe('EditItem', () => {
  let component: EditItem;
  let fixture: ComponentFixture<EditItem>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EditItem]
    })
    .compileComponents();

    fixture = TestBed.createComponent(EditItem);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
