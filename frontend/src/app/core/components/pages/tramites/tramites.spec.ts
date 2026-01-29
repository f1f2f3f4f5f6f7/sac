import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Tramites } from './tramites';

describe('Tramites', () => {
  let component: Tramites;
  let fixture: ComponentFixture<Tramites>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Tramites]
    })
    .compileComponents();

    fixture = TestBed.createComponent(Tramites);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
